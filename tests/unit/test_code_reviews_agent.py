"""Unit tests for the standards compliance checking functionality.

This module tests the core functionality for:
1. Generating prompts for compliance checking
2. Performing compliance checks against standards
3. Error handling for API and configuration issues
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from anthropic import AsyncAnthropic, AuthenticationError
from src.agents.code_reviews_agent import (
    generate_user_prompt,
    check_compliance,
    SYSTEM_PROMPT
)

@pytest.fixture
def mock_standard_content():
    """
    Provide mock standard content for testing.
    
    Returns:
        str: A sample standards document with requirements
    """
    return """# Test Standard
## Requirements
- Requirement 1
- Requirement 2"""

@pytest.fixture
def mock_codebase_content():
    """
    Provide mock codebase content for testing.
    
    Returns:
        str: A sample Python file content
    """
    return """# File: test.py
def test():
    print("Hello World")"""

@pytest.mark.asyncio
async def test_generate_user_prompt_includes_required_components():
    """
    Test prompt generation includes all necessary components.

    Given: Standard content and codebase content
    When: Generating a user prompt
    Then: Should include standards, codebase, and instructions
    """
    # Given
    standards = [{"_id": "test_id", "text": "Test standard content"}]
    codebase_content = "# File: test.py\ndef test():\n    print('Hello World')"

    # When
    prompt = await generate_user_prompt(standards, codebase_content)

    # Then
    assert "Test standard content" in prompt
    assert "test.py" in prompt
    assert "Hello World" in prompt

@pytest.mark.asyncio
async def test_check_compliance_handles_api_errors():
    """
    Test handling of API failures.

    Given: API that raises an error
    When: Performing a compliance check
    Then: Should return error report with details
    """
    # Given
    codebase_file = Path("test_codebase.txt")
    standards = [{"_id": "test_standard", "text": "Test standard content"}]
    review_id = "test_review_id"
    standard_set_name = "test_standard_set"

    error_response = {
        'type': 'error',
        'error': {
            'type': 'authentication_error',
            'message': 'invalid x-api-key'
        }
    }

    mock_client = AsyncMock()
    mock_client._request = AsyncMock(side_effect=AuthenticationError(
        message=f"Error code: 401 - {error_response}",
        response=MagicMock(status_code=401),
        body=error_response
    ))

    # When/Then
    with patch('anthropic.AsyncAnthropic', return_value=mock_client), \
         patch('builtins.open', create=True) as mock_open, \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):

        mock_open.return_value.__enter__.return_value.read.return_value = "Test content"
        with pytest.raises(AuthenticationError) as exc_info:
            await check_compliance(codebase_file, standards, review_id, standard_set_name)

        assert "invalid x-api-key" in str(exc_info.value)

@pytest.mark.asyncio
async def test_check_compliance_raises_error_without_api_key():
    """
    Test handling of missing API key.

    Given: No API key in environment
    When: Attempting a compliance check
    Then: Should raise ValueError with clear message
    """
    # Given
    codebase_file = Path("test_codebase.txt")
    standards = [{"_id": "test_standard", "text": "Test standard content"}]
    review_id = "test_review_id"
    standard_set_name = "test_standard_set"

    # When/Then
    with patch.dict('os.environ', clear=True), \
         patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "Test content"
        with pytest.raises(ValueError) as exc_info:
            await check_compliance(codebase_file, standards, review_id, standard_set_name)

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)