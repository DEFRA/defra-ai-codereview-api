"""Standards Checking Agent for compliance analysis."""
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import asyncio
from anthropic import AsyncAnthropic
from src.logging_config import setup_logger
from src.database import get_database
from bson import ObjectId

logger = setup_logger(__name__)

SYSTEM_PROMPT = """You are a code compliance analysis expert.
Analyze code against compliance standards.
Determine if code meets each standard.
Provide detailed recommendations for non-compliant areas.
Consider the codebase as a whole when evaluating compliance."""


async def generate_user_prompt(standard: Dict[str, Any], codebase_content: str) -> str:
    """Generate the user prompt for the Anthropic model."""
    # Log the standard being processed
    standard_preview = standard.get('text', '')[:150] + '...' if len(standard.get('text', '')) > 150 else standard.get('text', '')
    logger.debug(f"Processing standard ID: {standard.get('_id')}")
    logger.debug(f"Standard preview: {standard_preview}")

    prompt = f"""Given the standard below:
## Standard {standard['_id']}
{standard['text']}

Compare the entire codebase of the submitted repository below, to assess how well the standard is adhered to:
{codebase_content}

Determine if the codebase as a whole is compliant (true/false).
List specific files/sections in the codebase that are relevant to the standard (if any).
If non-compliant, provide concise recommendations - 1-2 sentences.
Consider dependencies and interactions between different parts of the code.

Generate a informative but concise compliance report using this format:

Replace the <span style="color: [COLOUR]"> with the appropriate hash code of the colour for the compliance status detailed below.
Yes = #00703c, No = #d4351c, Partially = #1d70b8

## Standard: [Standard Title from the standard text]

Compliant: <span style="color: [COLOUR]">**[Yes/No/Partially]**</span>

Relevant Files/Sections:
- [file/path/1]
- [file/path/2]

[Describe how the codebase implements or fails to implement this standard - keep this informative and concise]
[If partially compliant or non-compliant, explain specific issues - keep this informative and concise]

## [Standard Category 2]

[...repeat format for each standard...]

## Specific Recommendations

- [Describe specific change needed]
- [Additional action items as needed]
"""

    # Log the complete prompt and word count
    word_count = len(prompt.split())
    logger.debug(f"Generated prompt word count: {word_count}")

    return prompt


async def check_compliance(codebase_file: Path, standards: List[Dict[str, Any]], review_id: str, standard_set_name: str, matching_classification_ids: List[str]) -> Path:
    """Check codebase compliance against standards using Anthropic's Claude."""
    try:
        # Filter standards if LLM_TESTING is enabled
        if os.getenv("LLM_TESTING", "false").lower() == "true":
            testing_files = os.getenv("LLM_TESTING_STANDARDS_FILES", "").split(",")
            filtered_standards = []
            for standard in standards:
                repository_path = standard.get('repository_path', '')
                if any(test_file.strip() in repository_path for test_file in testing_files):
                    filtered_standards.append(standard)
            standards = filtered_standards
            logger.info(f"LLM Testing enabled - filtered to {len(standards)} matching standards")

        # Read codebase content
        with open(codebase_file, 'r', encoding='utf-8') as f:
            codebase_content = f.read()
        logger.debug(f"Codebase content length: {len(codebase_content)} characters")

        # Log total number of standards to process
        logger.debug(f"Total standards to process for {standard_set_name}: {len(standards)}")
        logger.debug("Standards to be processed:")
        for idx, std in enumerate(standards, 1):
            preview = std.get('text', '')[:150] + '...' if len(std.get('text', '')) > 150 else std.get('text', '')
            logger.info(f"{idx}. Standard ID: {std.get('_id')}, Preview: {preview}")

        # Get Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        anthropic = AsyncAnthropic(api_key=api_key)
        
        # Process each standard individually and collect reports
        reports = []
        for idx, standard in enumerate(standards, 1):
            # Generate prompt for individual standard
            prompt = await generate_user_prompt(standard, codebase_content)
            logger.debug(f"Generated prompt word count for standard {standard['_id']}: {len(prompt.split())}")

            # Call Claude for analysis
            logger.info(f"Starting compliance check for standard {idx}/{len(standards)}: {standard['_id']}")
            message = await anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            
            report_text = message.content[0].text
            reports.append(report_text)
            logger.debug(f"Completed standard {idx}/{len(standards)}: {standard['_id']}")
            logger.debug(f"Report length for standard {standard['_id']}: {len(report_text)} characters")
            logger.debug(f"Report preview: {report_text[:150]}...")
            
            # Add sleep between API calls to prevent rate limiting
            await asyncio.sleep(10)  # Sleep for 1 second between calls

        # Log report statistics
        logger.info(f"Total reports generated: {len(reports)}")
        
        # Get current date/time in GDS format (e.g. "22 January 2025 13:38:12")
        current_time = datetime.now().strftime("%d %B %Y %H:%M:%S")
        
        # Get database connection to fetch classification names
        db = await get_database()
        
        # Convert classification IDs to ObjectIds
        classification_obj_ids = [ObjectId(id) for id in matching_classification_ids]
        
        # Fetch classification names from database
        classifications = await db.classifications.find(
            {"_id": {"$in": classification_obj_ids}}
        ).to_list(None)
        
        # Extract classification names
        classification_names = [c.get('name', '') for c in classifications if c.get('name')]
        
        # Create header section with classification names
        header = f"""# {standard_set_name} Code Review
Date: {current_time}
Matched Classifications: {", ".join(classification_names) if classification_names else "None"}

"""
        
        # Combine header with all reports
        combined_report = header + "\n\n".join(reports)
        combined_report += "\n\n## Specific Recommendations\n\n"
        
        # Save combined report to file
        report_file = codebase_file.parent / f"{review_id}-{standard_set_name}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(combined_report)

        logger.info(f"Completed compliance check for standard set '{standard_set_name}', saved {len(reports)} reports to {report_file}")
        return report_file

    except Exception as e:
        logger.error(f"Error checking compliance: {str(e)}")
        raise
