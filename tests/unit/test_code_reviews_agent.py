"""Unit tests for the standards compliance checking functionality.

This module tests the core functionality for:
1. Generating prompts for compliance checking
2. Performing compliance checks against standards
3. Error handling for API and configuration issues
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
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
async def test_generate_user_prompt_includes_required_components(
    mock_standard_content,
    mock_codebase_content
):
    """
    Test prompt generation includes all necessary components.
    
    Given: Standard content and codebase content
    When: Generating a user prompt
    Then: Should include standards, codebase, and instructions
    """
    # When
    prompt = await generate_user_prompt(mock_standard_content, mock_codebase_content)
    
    # Then
    assert mock_standard_content in prompt
    assert mock_codebase_content in prompt
    assert "Compare the entire codebase" in prompt
    assert "Generate a informative but concise compliance report" in prompt

@pytest.mark.asyncio
async def test_check_compliance_generates_report_on_success():
    """
    Test successful compliance check workflow.
    
    Given: Valid files and working API connection
    When: Performing a compliance check
    Then: Should generate a compliance report
    """
    # Given
    codebase_file = Path("test_codebase.txt")
    standards_files = [Path("test_standard.txt")]
    
    mock_message = MagicMock()
    mock_message.text = "Test compliance report"
    mock_response = MagicMock()
    mock_response.content = [mock_message]
    
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    
    # When
    with patch('src.agents.code_reviews_agent.Anthropic', return_value=mock_client) as mock_anthropic, \
         patch('builtins.open', create=True) as mock_open, \
         patch('pathlib.Path.write_text') as mock_write, \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        
        mock_open.return_value.__enter__.return_value.read.side_effect = [
            "test codebase content",  # codebase file
            "test standard content",  # standard file
        ]
        
        result = await check_compliance(codebase_file, standards_files)
        
        # Then
        # Verify API call
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs['model'] == "claude-3-5-sonnet-20241022"
        assert call_kwargs['max_tokens'] == 4096
        assert call_kwargs['temperature'] == 0
        assert call_kwargs['system'] == SYSTEM_PROMPT
        
        # Verify report content
        assert "Test compliance report" in result

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
    standards_files = [Path("test_standard.txt")]
    
    # When/Then
    with patch.dict('os.environ', clear=True), \
         pytest.raises(ValueError) as exc_info:
        await check_compliance(codebase_file, standards_files)
    
    assert "ANTHROPIC_API_KEY environment variable is not set" in str(exc_info.value)

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
    standards_files = [Path("test_standard.txt")]
    
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API Error")
    
    # When
    with patch('src.agents.code_reviews_agent.Anthropic', return_value=mock_client) as mock_anthropic, \
         patch('builtins.open', create=True) as mock_open, \
         patch('pathlib.Path.write_text') as mock_write, \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        
        mock_open.return_value.__enter__.return_value.read.side_effect = [
            "test codebase content",  # codebase file
            "test standard content",  # standard file
        ]
        
        result = await check_compliance(codebase_file, standards_files)
        
        # Then
        assert "Error processing standard" in result
        assert "API Error" in result 