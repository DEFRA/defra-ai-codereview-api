"""Standards agent for processing standard sets."""
# stdlib
import os
import logging
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime, UTC

# third party
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from anthropic import Anthropic

# local
from src.utils.logging_utils import setup_logger
from src.utils.anthropic_client import AnthropicClient
from src.agents.git_repos_agent import download_repository
from src.repositories.classification_repo import ClassificationRepository
from src.repositories.standard_set_repo import StandardSetRepository
from src.models.classification import Classification
from src.config.config import settings
from src.database.database_utils import get_database

logger = setup_logger(__name__)


class StandardsError(Exception):
    """Base exception for standards processing errors."""
    pass


class StandardsProcessingError(StandardsError):
    """Error processing standards."""
    pass


class StandardAnalysisError(StandardsError):
    """Error analyzing standard with LLM."""
    pass


class StandardsConfig:
    """Configuration management for standards processing."""

    def __init__(self) -> None:
        self.llm_testing: bool = settings.LLM_TESTING
        self.testing_files: List[str] = (
            settings.LLM_TESTING_STANDARDS_FILES.split(",")
            if self.llm_testing else []
        )


async def process_standard_set(standard_set_id: str, repository_url: str):
    """Process a standard set in the background."""
    try:
        logger.debug(
            f"Starting to process standard set {standard_set_id} from repository {repository_url}")

        # Get database connection
        db = await get_database()

        # Get repositories
        repo = await download_repository(repository_url)

        # Get all classifications
        classifications = await get_classifications(db)

        # Process standards
        await process_standards(db, repo, standard_set_id, classifications)

        # Log completion
        logger.info(f"Successfully processed standard set {standard_set_id}")

        # Cleanup
        cleanup_repository(repo)
        logger.debug(f"Cleaned up repository at {repo}")

    except Exception as e:
        logger.error(f"Error processing standard set: {str(e)}", exc_info=True)
        raise StandardsProcessingError(str(e)) from e


async def get_classifications(db: AsyncIOMotorDatabase) -> List[Classification]:
    """Get all classifications from the database."""
    collection = db.get_collection("classifications")
    repo = ClassificationRepository(collection)
    classifications = await repo.get_all()
    logger.debug(
        f"Retrieved classifications: {[c.name for c in classifications]}")
    return classifications


def cleanup_repository(repo_path: Path):
    """Clean up the temporary repository directory."""
    logger.debug(f"Cleaning up repository directory at {repo_path}")
    shutil.rmtree(repo_path)


async def get_files_to_process(repo_path: Path, config: StandardsConfig) -> List[Tuple[str, str]]:
    """Get list of files to process based on configuration.

    Args:
        repo_path: Path to repository
        config: Standards configuration

    Returns:
        List of (root, filename) tuples to process
    """
    if config.llm_testing:
        logger.info("LLM testing mode enabled - using test standards files")
        logger.debug(f"Looking for test files: {config.testing_files}")
        files_to_process = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(repo_path)
                logger.debug(f"Checking file: {rel_path}")
                # Strip any extension for comparison
                file_base = file.rsplit('.', 1)[0]
                test_file_bases = [tf.rsplit('.', 1)[0]
                                   for tf in config.testing_files]
                if any(test_base.lower() == file_base.lower() for test_base in test_file_bases):
                    logger.debug(f"Found matching test file: {rel_path}")
                    files_to_process.append((root, file))
        logger.info(f"Found {len(files_to_process)} test files to process")
        return files_to_process

    # Process all markdown files
    return [
        (root, file)
        for root, _, files in os.walk(repo_path)
        for file in files
        if file.endswith('.md') and not file.lower() == 'readme.md' and not file.lower() == 'contributing.md'
    ]


async def process_standard_file(
    file_path: Path,
    repo_path: Path,
    standard_set_oid: ObjectId,
    classifications: List[Classification],
    standards_collection
) -> None:
    """Process a single standard file.

    Args:
        file_path: Path to the standard file
        repo_path: Base repository path
        standard_set_oid: ObjectId of the standard set
        classifications: List of available classifications
        standards_collection: MongoDB collection for standards

    Raises:
        StandardsProcessingError: If processing fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get classifications for this standard
        standard_classifications = await analyze_standard(
            content,
            [c.name for c in classifications]
        )
        logger.debug(
            f"Classifications for {file_path}: {standard_classifications}")

        # Create name to ID mapping for classifications
        classification_map = {c.name: c.id for c in classifications}

        # Convert classification names to IDs and ensure they are ObjectIds
        classification_ids = [
            ObjectId(str(classification_map[name]))
            for name in standard_classifications
            if name in classification_map
        ]

        # Create standard document
        standard_doc = {
            "_id": ObjectId(),
            "text": content,
            "repository_path": str(file_path.relative_to(repo_path)),
            "standard_set_id": standard_set_oid,
            "classification_ids": classification_ids,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        # Insert standard
        result = await standards_collection.insert_one(standard_doc)
        logger.debug(
            f"Inserted standard document with ID: {result.inserted_id}")

    except Exception as e:
        raise StandardsProcessingError(
            f"Error processing standard {file_path}: {str(e)}") from e


async def process_standards(
    db: AsyncIOMotorDatabase,
    repo_path: Path,
    standard_set_id: str,
    classifications: List[Classification]
):
    """Process standards in the repository."""
    logger.debug(f"Starting to process standards for set {standard_set_id}")

    try:
        # Get standards collection
        standards_collection = db.get_collection("standards")

        # Convert standard_set_id to ObjectId
        standard_set_oid = ObjectId(standard_set_id)

        # Delete any existing standards for this set
        await standards_collection.delete_many({"standard_set_id": standard_set_oid})

        # Get files to process based on configuration
        config = StandardsConfig()
        files_to_process = await get_files_to_process(repo_path, config)

        # Process each file
        for root, file in files_to_process:
            file_path = Path(root) / file
            logger.debug(f"Processing standard file: {file_path}")
            try:
                await process_standard_file(
                    file_path,
                    repo_path,
                    standard_set_oid,
                    classifications,
                    standards_collection
                )
            except StandardsProcessingError as e:
                logger.error(str(e))
                continue

    except Exception as e:
        raise StandardsProcessingError(
            f"Error processing standards: {str(e)}") from e


async def analyze_standard(content: str, classifications: List[str]) -> List[str]:
    """Use LLM to analyze standard and determine relevant classifications.

    Args:
        content: Content of the standard to analyze
        classifications: List of available classification names

    Returns:
        List of classification names that apply to the standard

    Raises:
        StandardAnalysisError: If analysis fails
    """
    logger.debug("Starting standard analysis with LLM")

    # Create prompt
    prompt = f"""You are a standards analysis expert. Given a standard's content and a list of possible classifications, determine which classifications apply to this standard.

Classifications: {", ".join(classifications)}

Standard Content:
{content}

Please analyze the standard and determine which classifications apply. A standard can be "universal" (applies to all codebases) or have specific classifications.

First, determine if this is a universal standard that applies to all codebases regardless of technology.
- A universal standard is one that applies to all codebases regardless of technology, so it should be applied to all codebases.
- Use the title and sub headers of the standard to help determine if it is universal.
- For example, a "security" standard is universal because it applies to all codebases. "Docker" may be universal if it applies to all codebases AND 'Docker' is not in the Classifications list.
- think "does this standard apply to all codebases regardless of technology?", if so, then return an empty list.
If it is universal, return an empty list.
If it is not universal, return a list of relevant classification names from the provided list.

Return your response in a comma-separated list format, or return an empty list for universal standards.
Only return the list, no other text."""

    try:
        # Get response from Claude using utility client
        response = await AnthropicClient.create_message(
            prompt=prompt,
            system_prompt="You are a standards analysis expert that helps determine which technology classifications apply to software development standards."
        )

        # Parse response
        response = response.strip()
        logger.debug(f"LLM response: {response}")

        if not response:
            logger.debug(
                "Empty response from LLM, returning empty classifications list")
            return []

        # Split response into list and clean up
        classifications_result = [c.strip() for c in response.split(",")]
        logger.debug(
            f"Parsed classifications from LLM: {classifications_result}")

        # Validate classifications
        valid_classifications = [
            c for c in classifications_result
            if c in classifications
        ]
        logger.debug(
            f"Valid classifications after filtering: {valid_classifications}")

        return valid_classifications

    except Exception as e:
        raise StandardAnalysisError(
            f"Error analyzing standard: {str(e)}") from e
