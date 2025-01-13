"""Unit tests for standards_agent.py."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from src.agents.standards_agent import (
    generate_user_prompt,
    check_compliance,
    SYSTEM_PROMPT
)

@pytest.fixture
def mock_standard_content():
    """Mock standard content for testing."""
    return """# Test Standard
## Requirements
- Requirement 1
- Requirement 2"""

@pytest.fixture
def mock_codebase_content():
    """Mock codebase content for testing."""
    return """# File: test.py
def test():
    print("Hello World")"""

@pytest.mark.asyncio
async def test_generate_user_prompt(mock_standard_content, mock_codebase_content):
    """Test generate_user_prompt function."""
    prompt = await generate_user_prompt(mock_standard_content, mock_codebase_content)
    
    # Check prompt contains required components
    assert mock_standard_content in prompt
    assert mock_codebase_content in prompt
    assert "Compare the entire codebase" in prompt
    assert "Generate a informative but concise compliance report" in prompt

@pytest.mark.asyncio
async def test_check_compliance_success():
    """Test check_compliance function with successful API response."""
    codebase_file = Path("test_codebase.txt")
    standards_files = [Path("test_standard.txt")]
    
    mock_message = MagicMock()
    mock_message.text = "Test compliance report"
    mock_response = MagicMock()
    mock_response.content = [mock_message]
    
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    
    with patch('src.agents.standards_agent.Anthropic', return_value=mock_client) as mock_anthropic, \
         patch('builtins.open', create=True) as mock_open, \
         patch('pathlib.Path.write_text') as mock_write, \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        
        # Setup mock file contents
        mock_open.return_value.__enter__.return_value.read.side_effect = [
            "test codebase content",  # codebase file
            "test standard content",  # standard file
        ]
        
        result = await check_compliance(codebase_file, standards_files)
        
        # Verify Anthropic API was called correctly
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs['model'] == "claude-3-sonnet-20240229"
        assert call_kwargs['max_tokens'] == 4096
        assert call_kwargs['temperature'] == 0
        assert call_kwargs['system'] == SYSTEM_PROMPT
        
        # Verify report was generated
        assert "Test compliance report" in result

@pytest.mark.asyncio
async def test_check_compliance_missing_api_key():
    """Test check_compliance function with missing API key."""
    codebase_file = Path("test_codebase.txt")
    standards_files = [Path("test_standard.txt")]
    
    with patch.dict('os.environ', clear=True), \
         pytest.raises(ValueError) as exc_info:
        await check_compliance(codebase_file, standards_files)
    
    assert "ANTHROPIC_API_KEY environment variable is not set" in str(exc_info.value)

@pytest.mark.asyncio
async def test_check_compliance_api_error():
    """Test check_compliance function with API error."""
    codebase_file = Path("test_codebase.txt")
    standards_files = [Path("test_standard.txt")]
    
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API Error")
    
    with patch('src.agents.standards_agent.Anthropic', return_value=mock_client) as mock_anthropic, \
         patch('builtins.open', create=True) as mock_open, \
         patch('pathlib.Path.write_text') as mock_write, \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        
        # Setup mock file contents
        mock_open.return_value.__enter__.return_value.read.side_effect = [
            "test codebase content",  # codebase file
            "test standard content",  # standard file
        ]
        
        result = await check_compliance(codebase_file, standards_files)
        
        # Verify error was handled and included in report
        assert "Error processing standard" in result
        assert "API Error" in result 