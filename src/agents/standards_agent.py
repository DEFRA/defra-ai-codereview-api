"""Standards agent for processing standard sets."""
import os
import git
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime, UTC
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.logging_config import setup_logger
from src.agents.git_repos_agent import clone_repo
from src.repositories.classification_repo import ClassificationRepository
from src.repositories.standard_set_repo import StandardSetRepository
from src.models.classification import Classification
from anthropic import Anthropic
from src.config import settings

logger = setup_logger(__name__)

async def process_standard_set(standard_set_id: str, repository_url: str):
    """Process a standard set in the background."""
    try:
        logger.debug(f"Starting to process standard set {standard_set_id} from repository {repository_url}")
        
        # Get database connection
        from src.database import get_database
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

async def download_repository(repository_url: str) -> Path:
    """Download the repository to a temporary directory."""
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    await clone_repo(repository_url, temp_dir)
    logger.debug(f"Repository cloned successfully to {temp_dir}")
    return temp_dir

async def get_classifications(db: AsyncIOMotorDatabase) -> List[Classification]:
    """Get all classifications from the database."""
    collection = db.get_collection("classifications")
    repo = ClassificationRepository(collection)
    classifications = await repo.get_all()
    logger.debug(f"Retrieved classifications: {[c.name for c in classifications]}")
    return classifications

def cleanup_repository(repo_path: Path):
    """Clean up the temporary repository directory."""
    import shutil
    logger.debug(f"Cleaning up repository directory at {repo_path}")
    shutil.rmtree(repo_path)

async def process_standards(
    db: AsyncIOMotorDatabase,
    repo_path: Path,
    standard_set_id: str,
    classifications: List[Classification]
):
    """Process standards in the repository."""
    logger.debug(f"Starting to process standards for set {standard_set_id}")
    
    # Get standards collection
    standards_collection = db.get_collection("standards")
    
    # Delete any existing standards for this set
    result = await standards_collection.delete_many({"standard_set_id": standard_set_id})
    
    # Create name to ID mapping for classifications
    classification_map = {c.name: str(c.id) for c in classifications}
    
    # If LLM testing is enabled, only process specified test files
    if settings.LLM_TESTING:
        logger.info("LLM testing mode enabled - using test standards files")
        test_files = [x.strip() for x in settings.LLM_TESTING_STANDARDS_FILES.split(",") if x.strip()]
        logger.debug(f"Looking for test files: {test_files}")
        files_to_process = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(repo_path)
                logger.debug(f"Checking file: {rel_path}")
                # Strip any extension for comparison
                file_base = file.rsplit('.', 1)[0]
                test_file_bases = [tf.rsplit('.', 1)[0] for tf in test_files]
                if any(test_base.lower() == file_base.lower() for test_base in test_file_bases):
                    logger.debug(f"Found matching test file: {rel_path}")
                    files_to_process.append((root, file))
        logger.info(f"Found {len(files_to_process)} test files to process")
    else:
        # Process all markdown files
        files_to_process = [
            (root, file) 
            for root, _, files in os.walk(repo_path)
            for file in files 
            if file.endswith('.md') and not file.lower() == 'readme.md' and not file.lower() == 'contributing.md'
        ]
    
    # Process files
    for root, file in files_to_process:
        file_path = Path(root) / file
        logger.debug(f"Processing standard file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Get classifications for this standard
            standard_classifications = await analyze_standard(
                content,
                [c.name for c in classifications]
            )
            logger.debug(f"Classifications for {file_path}: {standard_classifications}")
            
            # Convert classification names to IDs
            classification_ids = [
                ObjectId(classification_map[name])
                for name in standard_classifications
                if name in classification_map
            ]
            
            # Create standard document
            standard_doc = {
                "_id": ObjectId(),
                "text": content,
                "repository_path": str(file_path.relative_to(repo_path)),
                "standard_set_id": standard_set_id,
                "classification_ids": classification_ids,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
            
            # Insert standard
            result = await standards_collection.insert_one(standard_doc)
            logger.debug(f"Inserted standard document with ID: {result.inserted_id}")
            
        except Exception as e:
            logger.error(f"Error processing standard {file}: {str(e)}")
            continue

async def analyze_standard(content: str, classifications: List[str]) -> List[str]:
    """Use LLM to analyze standard and determine relevant classifications."""
    logger.debug("Starting standard analysis with LLM")
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
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
        # Get response from Claude
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            temperature=0,
            system="You are a standards analysis expert that helps determine which technology classifications apply to software development standards.",
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Parse response - safely access content
        response = message.content[0].text.strip() if message.content else ""
        logger.debug(f"LLM response: {response}")
        
        if not response:
            logger.debug("Empty response from LLM, returning empty classifications list")
            return []
            
        # Split response into list and clean up
        classifications_result = [c.strip() for c in response.split(",")]
        logger.debug(f"Parsed classifications from LLM: {classifications_result}")
        
        # Validate classifications
        valid_classifications = [
            c for c in classifications_result 
            if c in classifications
        ]
        logger.debug(f"Valid classifications after filtering: {valid_classifications}")
        
        return valid_classifications
        
    except Exception as e:
        logger.error(f"Error during LLM analysis: {str(e)}", exc_info=True)
        return [] 