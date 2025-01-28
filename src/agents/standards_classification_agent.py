"""Standards Classification Agent for determining relevant technology classifications."""
import os
from pathlib import Path
from typing import List
from anthropic import AsyncAnthropic
from src.logging_config import setup_logger
from src.models.classification import Classification

logger = setup_logger(__name__)

SYSTEM_PROMPT = """You are a technology stack analysis expert."""

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
    """
    try:
        # Read codebase content
        codebase_content = ""
        for root, _, files in os.walk(codebase_path):
            for file in files:
                # Skip binary files and common non-code files
                if file.endswith(('.jpg', '.png', '.gif', '.pdf', '.zip')):
                    continue
                    
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        codebase_content += f"\n=== {file} ===\n"
                        codebase_content += f.read()
                except UnicodeDecodeError:
                    # Skip binary files
                    continue
                    
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
        logger.debug("Available classifications: %s", [c.name for c in classifications])

        # Get Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        anthropic = AsyncAnthropic(api_key=api_key)

        # Call Claude for analysis
        logger.info("Starting codebase classification analysis")
        message = await anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        response = message.content[0].text.strip()
        logger.debug("Raw LLM response:\n%s", response)
        
        if not response:
            logger.info("No classifications found in LLM response")
            return []
            
        # Clean and parse classification names more strictly
        classification_names = []
        # First remove any explanatory text by finding the last line with actual classifications
        response_lines = response.strip().split('\n')
        actual_response = response_lines[-1]  # Take the last non-empty line
        for line in reversed(response_lines):
            if ',' in line:  # Found a line with comma-separated values
                actual_response = line
                break

        # Now parse the comma-separated values
        for name in actual_response.split(","):
            cleaned = name.strip().strip('"').strip()  # Remove quotes and extra spaces
            # Check for exact match in available classifications
            for classification in classifications:
                if cleaned.lower() == classification.name.lower():  # Case-insensitive comparison
                    classification_names.append(classification.name)  # Use exact name from classification
                    break
                
        logger.debug("Parsed classification names: %s", classification_names)
        
        matching_ids = [
            c.id for c in classifications 
            if c.name in classification_names
        ]
        
        logger.info("Found matching classification IDs: %s", matching_ids)
        return matching_ids

    except Exception as e:
        logger.error(f"Error analyzing codebase classifications: {str(e)}")
        raise
