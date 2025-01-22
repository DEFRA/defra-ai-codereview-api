"""Standards Classification Agent for determining relevant technology classifications."""
import os
from pathlib import Path
from typing import List
from anthropic import AsyncAnthropic
from src.logging_config import setup_logger
from src.models.classification import Classification

logger = setup_logger(__name__)

SYSTEM_PROMPT = """You are a technology stack analysis expert.
Analyze codebases to determine which technologies and programming languages are used.
Consider all aspects including code files, configuration files, and dependencies."""

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
        prompt = f"""Analyze this codebase and identify which technology classifications are used from the list below. Provide your answer as a comma-separated list of ONLY the matching technology categories (e.g., "Python, Node.js"). Return ONLY the list - no explanations or additional text. Return an empty string if no matches are found.

Available Technology Classifications:
{", ".join([c.name for c in classifications])}

Codebase Files and Content:
{codebase_content}

Key areas to consider:
1. Programming languages
2. Frameworks & libraries
3. Build tools & package managers
4. Config files
5. Infrastructure & deployment

Example outputs:
- "Python, React, Docker"
- "Java, Spring Boot, Maven"
- "" (empty string if no matches)
"""

        # Log the prompt and available classifications
        logger.debug("Available classifications: %s", [c.name for c in classifications])
        logger.debug("Generated prompt:\n%s", prompt)

        # Get Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        anthropic = AsyncAnthropic(api_key=api_key)

        # Call Claude for analysis
        logger.info("Starting codebase classification analysis")
        message = await anthropic.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        response = message.content[0].text.strip()
        logger.debug("Raw LLM response:\n%s", response)
        
        if not response:
            logger.info("No classifications found in LLM response")
            return []
            
        # Get classification IDs that match the response
        classification_names = [name.strip() for name in response.split(",")]
        logger.debug("Parsed classification names: %s", classification_names)
        
        matching_ids = [
            str(c.id) for c in classifications 
            if c.name in classification_names
        ]
        
        logger.info("Found matching classification IDs: %s", matching_ids)
        return matching_ids

    except Exception as e:
        logger.error(f"Error analyzing codebase classifications: {str(e)}")
        raise
