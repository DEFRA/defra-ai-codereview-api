"""Standards Classification Agent for determining relevant technology classifications."""
import os
from pathlib import Path
from typing import List, Dict, Any
from src.utils.anthropic_client import AnthropicClient
from src.utils.logging_utils import setup_logger
from src.models.classification import Classification

logger = setup_logger(__name__)

# Constants
BINARY_EXTENSIONS = ('.jpg', '.png', '.gif', '.pdf', '.zip')
SYSTEM_PROMPT = """You are a technology stack analysis expert."""


class ClassificationError(Exception):
    """Base exception for classification errors."""
    pass


class CodebaseReadError(ClassificationError):
    """Error reading codebase files."""
    pass


class ClassificationAnalysisError(ClassificationError):
    """Error analyzing classifications."""
    pass


class ResponseParsingError(ClassificationError):
    """Error parsing LLM response."""
    pass


class ClassificationConfig:
    """Configuration management for classification analysis."""

    def __init__(self) -> None:
        self.binary_extensions = BINARY_EXTENSIONS


async def read_codebase_content(codebase_path: Path) -> str:
    """Read and concatenate codebase content.

    Args:
        codebase_path: Path to the codebase directory

    Returns:
        Concatenated codebase content

    Raises:
        CodebaseReadError: If reading files fails
    """
    try:
        codebase_content = ""
        for root, _, files in os.walk(codebase_path):
            for file in files:
                if file.endswith(BINARY_EXTENSIONS):
                    continue

                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        codebase_content += f"\n=== {file} ===\n"
                        codebase_content += f.read()
                except UnicodeDecodeError:
                    continue

        return codebase_content

    except Exception as e:
        raise CodebaseReadError(f"Failed to read codebase: {str(e)}") from e


async def parse_classification_response(
    response: str,
    classifications: List[Classification]
) -> List[str]:
    """Parse and validate LLM classification response.

    Args:
        response: Raw LLM response
        classifications: List of available classifications

    Returns:
        List of validated classification names

    Raises:
        ResponseParsingError: If parsing fails
    """
    try:
        if not response:
            logger.info("No classifications found in LLM response")
            return []

        # Find line with classifications
        response_lines = response.strip().split('\n')
        actual_response = response_lines[-1]
        for line in reversed(response_lines):
            if ',' in line:
                actual_response = line
                break

        # Parse and validate classifications
        classification_names = []
        for name in actual_response.split(","):
            cleaned = name.strip().strip('"').strip()
            for classification in classifications:
                if cleaned.lower() == classification.name.lower():
                    classification_names.append(classification.name)
                    break

        logger.debug("Parsed classification names: %s", classification_names)
        return classification_names

    except Exception as e:
        raise ResponseParsingError(
            f"Failed to parse response: {str(e)}") from e


async def analyze_codebase_classifications(
    codebase_path: Path,
    classifications: List[Classification]
) -> List[str]:
    """Analyze codebase to determine relevant classifications.

    Args:
        codebase_path: Path to the codebase directory
        classifications: List of available classifications

    Returns:
        List of classification IDs that match the codebase

    Raises:
        ClassificationError: If analysis fails
    """
    try:
        # Read codebase content
        codebase_content = await read_codebase_content(codebase_path)

        # Generate prompt
        prompt = f"""Analyze this codebase and identify which technology classifications are used from the list below.

Examples of valid responses:
"Python, React, Docker"
"Java, Spring Boot"
"Node.js, TypeScript"
"" (if no matches to the available classifications list below)

Available Classifications:
{", ".join([c.name for c in classifications])}

Codebase Files and Content:
{codebase_content}

CRITICAL:
- Your response must ONLY contain a comma-separated list of matching classifications ONLY from the list below.
- DO NOT include any other text, explanations, or formatting.
- Only include classifications that are present in the codebase.
"""

        # Log the prompt and available classifications
        logger.debug("Available classifications: %s", [
                     c.name for c in classifications])
        logger.debug("\n=== PROMPT BEING SENT TO ANTHROPIC ===\n" +
                     prompt + "\n=== END PROMPT ===\n")
        logger.debug(f"Prompt length (chars): {len(prompt)}")

        # Call Claude for analysis
        logger.info("Starting codebase classification analysis")
        response = await AnthropicClient.create_message(prompt=prompt, system_prompt=SYSTEM_PROMPT)

        # Parse response
        response = response.strip()
        logger.debug("Raw LLM response:\n%s", response)

        # Parse classifications
        classification_names = await parse_classification_response(response, classifications)

        # Get matching IDs
        matching_ids = [
            c.id for c in classifications
            if c.name in classification_names
        ]

        logger.info("Found matching classification IDs: %s", matching_ids)
        return matching_ids

    except Exception as e:
        raise ClassificationError(
            f"Classification analysis failed: {str(e)}") from e
