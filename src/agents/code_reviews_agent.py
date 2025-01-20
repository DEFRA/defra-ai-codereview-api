"""Standards Checking Agent for compliance analysis."""
import os
from pathlib import Path
from typing import List
from anthropic import AsyncAnthropic
from src.logging_config import setup_logger

logger = setup_logger(__name__)

SYSTEM_PROMPT = """You are a code compliance analysis expert.
Analyze code against compliance standards.
Determine if code meets each standard.
Provide detailed recommendations for non-compliant areas.
Consider the codebase as a whole when evaluating compliance."""


async def generate_user_prompt(standards: List[dict], codebase_content: str) -> str:
    """Generate the user prompt for the Anthropic model."""
    # Combine all standards into a single string
    standards_content = "\n\n".join([f"## Standard {std['_id']}\n{std['text']}" for std in standards])
    
    prompt = f"""Given the set of standards below:
{standards_content}

Compare the entire codebase of the submitted repository below, to assess how well the relevant standards are adhered to:
{codebase_content}

For each standard:
- Determine if the codebase as a whole is compliant (true/false)
- List specific files/sections in the codebase that are relevant to the standard (if any)
- If non-compliant, provide concise recommendations - 1-2 sentences
- Consider dependencies and interactions between different parts of the code

Generate a informative but concise compliance report that includes:
- Per-standard analysis
- Specific recommendations for improvements

Below is a example of the report format (Replace all text in [brackets] with actual content - don't leave the square brackets in the final report):

Replace the <span style="color: [COLOUR]"> with the appropriate hash code of the colour for the compliance status detailed below.
Yes = #00703c, No = #d4351c, Partially = #1d70b8

## [Standard Category 1]

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


async def check_compliance(codebase_file: Path, standards: List[dict], review_id: str, standard_set_name: str) -> Path:
    """Check codebase compliance against standards using Anthropic's Claude."""
    try:
        # Read codebase content
        with open(codebase_file, 'r', encoding='utf-8') as f:
            codebase_content = f.read()
        logger.debug(f"Codebase content length: {len(codebase_content)} characters")

        # Generate prompt
        prompt = await generate_user_prompt(standards, codebase_content)
        logger.debug(f"Generated prompt word count: {len(prompt.split())}")

        # Get Anthropic client
        anthropic = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Call Claude for analysis
        logger.info("Starting compliance check")
        message = await anthropic.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        report = message.content[0].text
        logger.debug(f"Generated report length: {len(report)} characters")

        # Save report to file using required format: {code-review-record-id}-{standard-set-name}.md
        report_file = codebase_file.parent / f"{review_id}-{standard_set_name}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Completed compliance check for standard set '{standard_set_name}', report saved to {report_file}")
        return report_file

    except Exception as e:
        logger.error(f"Error checking compliance: {str(e)}")
        raise
