"""Unit tests for the standards classification agent functionality.

This module tests the core functionality for:
1. Analyzing codebases to determine technology classifications
2. Error handling for API and configuration issues
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from bson import ObjectId
from anthropic import AsyncAnthropic, AuthenticationError
from src.agents.standards_classification_agent import analyze_codebase_classifications
from src.models.classification import Classification

@pytest.fixture
def mock_classifications():
    """Provide mock classifications for testing."""
    return [
        Classification(id=ObjectId("507f1f77bcf86cd799439011"), name="Python"),
        Classification(id=ObjectId("507f1f77bcf86cd799439012"), name="Node.js"),
        Classification(id=ObjectId("507f1f77bcf86cd799439013"), name="Docker")
    ]

@pytest.fixture
def mock_codebase_path(tmp_path):
    """Create a temporary mock codebase for testing."""
    # Create test files
    codebase = tmp_path / "test_codebase"
    codebase.mkdir()
    
    # Python file
    python_file = codebase / "main.py"
    python_file.write_text("def hello(): print('Hello World')")
    
    # Binary file (should be skipped)
    binary_file = codebase / "binary.dat"
    binary_file.write_bytes(bytes([0xFF, 0xD8, 0xFF, 0xE0]))  # JPEG magic numbers
    
    # Common non-code files (should be skipped)
    (codebase / "image.jpg").write_text("Not a real image")
    (codebase / "doc.pdf").write_text("Not a real PDF")
    
    return codebase

@pytest.mark.asyncio
async def test_analyze_codebase_successful(mock_codebase_path, mock_classifications):
    """
    Test successful codebase analysis.
    
    Given: Valid codebase and classifications
    When: Analyzing the codebase
    Then: Should return matching classification IDs
    """
    # Create mock Anthropic response
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Python, Docker")]
    
    class MockMessages:
        async def create(self, *args, **kwargs):
            return mock_message
            
    class MockAnthropic:
        def __init__(self, api_key):
            self.messages = MockMessages()
    
    # When/Then
    with patch('src.agents.standards_classification_agent.AsyncAnthropic', MockAnthropic), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        result = await analyze_codebase_classifications(mock_codebase_path, mock_classifications)
        
        assert set(result) == {str(ObjectId("507f1f77bcf86cd799439011")), str(ObjectId("507f1f77bcf86cd799439013"))}  # Python and Docker IDs

@pytest.mark.asyncio
async def test_analyze_codebase_no_matches(mock_codebase_path, mock_classifications):
    """
    Test codebase analysis with no matches.
    
    Given: Valid codebase but no matching classifications
    When: Analyzing the codebase
    Then: Should return empty list
    """
    # Create mock Anthropic response
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="")]
    
    class MockMessages:
        async def create(self, *args, **kwargs):
            return mock_message
            
    class MockAnthropic:
        def __init__(self, api_key):
            self.messages = MockMessages()
    
    # When/Then
    with patch('src.agents.standards_classification_agent.AsyncAnthropic', MockAnthropic), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        result = await analyze_codebase_classifications(mock_codebase_path, mock_classifications)
        
        assert result == []

@pytest.mark.asyncio
async def test_analyze_codebase_missing_api_key(mock_codebase_path, mock_classifications):
    """
    Test handling of missing API key.
    
    Given: No API key in environment
    When: Attempting codebase analysis
    Then: Should raise ValueError
    """
    with patch.dict('os.environ', clear=True):
        with pytest.raises(ValueError) as exc_info:
            await analyze_codebase_classifications(mock_codebase_path, mock_classifications)
        
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

@pytest.mark.asyncio
async def test_analyze_codebase_api_error(mock_codebase_path, mock_classifications):
    """
    Test handling of API errors.
    
    Given: API that raises an error
    When: Analyzing codebase
    Then: Should propagate error
    """
    error_response = {
        'type': 'error',
        'error': {
            'type': 'authentication_error',
            'message': 'invalid x-api-key'
        }
    }
    
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=AuthenticationError(
        message=f"Error code: 401 - {error_response}",
        response=MagicMock(status_code=401),
        body=error_response
    ))
    
    with patch('src.agents.standards_classification_agent.AsyncAnthropic', return_value=mock_client), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        with pytest.raises(AuthenticationError) as exc_info:
            await analyze_codebase_classifications(mock_codebase_path, mock_classifications)
            
        assert "invalid x-api-key" in str(exc_info.value)

@pytest.mark.asyncio
async def test_analyze_codebase_binary_files(mock_codebase_path, mock_classifications):
    """
    Test handling of binary files.
    
    Given: Codebase with binary files
    When: Analyzing codebase
    Then: Should skip binary files and continue analysis
    """
    # Create mock Anthropic response
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Python")]
    
    class MockMessages:
        async def create(self, *args, **kwargs):
            # Verify binary file content not in prompt
            prompt = kwargs.get("messages", [{}])[0].get("content", "")
            assert "binary.dat" in prompt  # File should be listed
            assert "JFIF" not in prompt  # Binary content should be skipped
            return mock_message
            
    class MockAnthropic:
        def __init__(self, api_key):
            self.messages = MockMessages()
    
    # When/Then
    with patch('src.agents.standards_classification_agent.AsyncAnthropic', MockAnthropic), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        result = await analyze_codebase_classifications(mock_codebase_path, mock_classifications)
        
        assert result == [str(ObjectId("507f1f77bcf86cd799439011"))]  # Only Python ID

@pytest.mark.asyncio
async def test_analyze_codebase_general_error(mock_codebase_path, mock_classifications):
    """
    Test handling of general errors.
    
    Given: A function that raises an unexpected error
    When: Analyzing codebase
    Then: Should log and re-raise the error
    """
    test_error = RuntimeError("Test error")
    
    with patch('src.agents.standards_classification_agent.AsyncAnthropic', side_effect=test_error), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        with pytest.raises(RuntimeError) as exc_info:
            await analyze_codebase_classifications(mock_codebase_path, mock_classifications)
            
        assert str(test_error) in str(exc_info.value)

@pytest.mark.asyncio
async def test_analyze_codebase_skip_non_code_files(mock_codebase_path, mock_classifications):
    """
    Test skipping of common non-code files.
    
    Given: Codebase with common non-code files
    When: Analyzing codebase
    Then: Should skip non-code files and continue analysis
    """
    # Create mock Anthropic response
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Python")]
    
    class MockMessages:
        async def create(self, *args, **kwargs):
            # Verify non-code files are not in prompt
            prompt = kwargs.get("messages", [{}])[0].get("content", "")
            assert "main.py" in prompt  # Code file should be included
            assert "image.jpg" not in prompt  # Non-code files should be skipped
            assert "doc.pdf" not in prompt
            return mock_message
            
    class MockAnthropic:
        def __init__(self, api_key):
            self.messages = MockMessages()
    
    # When/Then
    with patch('src.agents.standards_classification_agent.AsyncAnthropic', MockAnthropic), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        result = await analyze_codebase_classifications(mock_codebase_path, mock_classifications)
        
        assert result == [str(ObjectId("507f1f77bcf86cd799439011"))]  # Only Python ID 