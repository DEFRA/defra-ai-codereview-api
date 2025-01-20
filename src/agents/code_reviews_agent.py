"""Standards Checking Agent for compliance analysis."""
import os
from pathlib import Path
from typing import List
from anthropic import Anthropic
from src.logging_config import setup_logger

logger = setup_logger(__name__)

SYSTEM_PROMPT = """You are a code compliance analysis expert.
Analyze code against compliance standards.
Determine if code meets each standard.
Provide detailed recommendations for non-compliant areas.
Consider the codebase as a whole when evaluating compliance."""


async def generate_user_prompt(standard_content: str, codebase_content: str) -> str:
    """Generate the user prompt for the Anthropic model."""
    prompt = f"""Given the set of standards below:
{standard_content}

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


async def check_compliance(codebase_file: Path, standards_files: List[Path]) -> str:
    """Check codebase compliance against standards using Anthropic's Claude."""
    logger.info("Starting compliance check")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    client = Anthropic(api_key=api_key)
    model = "claude-3-5-sonnet-20241022"

    # Read codebase content
    with open(codebase_file, 'r', encoding='utf-8') as f:
        codebase_content = f.read()
        logger.debug(f"Codebase content length: {
                     len(codebase_content)} characters")

    # Initialize the report file
    report_path = Path("data") / "compliance_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Code Compliance Report\n\n")

    final_report = ""

    # Process each standard
    for standard_file in standards_files:
        logger.debug(f"Processing standard: {standard_file}")

        with open(standard_file, 'r', encoding='utf-8') as f:
            standard_content = f.read()
            logger.debug(f"Standard content length: {
                         len(standard_content)} characters")

        user_prompt = await generate_user_prompt(standard_content, codebase_content)

        try:
            logger.debug("Sending request to Anthropic API")

            response = client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # Format the standard name by:
            # 1. Remove all extensions (.md and .txt)
            # 2. Replace underscores with spaces
            # 3. Title case each word
            standard_name = standard_file.stem.split(
                '.')[0].replace('_', ' ').title()

            # Append this response to the report file immediately
            standard_section = f"\n# {standard_name}\n\n{
                response.content[0].text}\n\n---\n\n"
            with open(report_path, 'a', encoding='utf-8') as f:
                f.write(standard_section)

            # Also keep track of the content for the return value
            final_report += standard_section

        except Exception as e:
            standard_name = standard_file.stem.split(
                '.')[0].replace('_', ' ').title()
            error_message = f"\n# {
                standard_name}\n\nError processing standard: {str(e)}\n"
            logger.error(f"Error processing standard {
                         standard_file}: {str(e)}")

            # Append error to the report file immediately
            with open(report_path, 'a', encoding='utf-8') as f:
                f.write(error_message)

            # Also keep track of the content for the return value
            final_report += error_message

    logger.info("Finished compliance check")
    return final_report
