"""Unit tests for the Standards Classification Agent."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from bson import ObjectId
from src.agents.standards_classification_agent import (
    analyze_codebase_classifications,
    CodebaseReadError,
    ResponseParsingError,
    ClassificationError
)
from src.models.classification import Classification

# Test Data
MOCK_CLASSIFICATIONS = [
    Classification(id=ObjectId("507f1f77bcf86cd799439011"), name="Python", description="Python language"),
    Classification(id=ObjectId("507f1f77bcf86cd799439012"), name="React", description="React framework"),
    Classification(id=ObjectId("507f1f77bcf86cd799439013"), name="Docker", description="Docker container")
]

MOCK_CODEBASE_CONTENT = """
=== main.py ===
import fastapi
from typing import List

app = fastapi.FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World"}
"""

@pytest.fixture
def mock_codebase_path(tmp_path):
    """Create a temporary mock codebase directory."""
    codebase_dir = tmp_path / "mock_codebase"
    codebase_dir.mkdir()
    
    # Create a sample Python file
    main_py = codebase_dir / "main.py"
    main_py.write_text(MOCK_CODEBASE_CONTENT)
    
    return codebase_dir

@pytest.fixture
def mock_anthropic_client():
    """Mock the Anthropic client responses."""
    with patch('src.agents.standards_classification_agent.AnthropicClient') as mock:
        mock.create_message = AsyncMock(return_value="Python")
        yield mock

async def test_analyze_codebase_classifications_identifies_python(mock_codebase_path, mock_anthropic_client):
    """Test successful identification of Python in codebase."""
    # Given a Python codebase
    # When analyzing the codebase for classifications
    result = await analyze_codebase_classifications(mock_codebase_path, MOCK_CLASSIFICATIONS)
    
    # Then Python should be identified and LLM should be called once
    assert result == [MOCK_CLASSIFICATIONS[0].id]  # Python classification ID
    mock_anthropic_client.create_message.assert_called_once()

async def test_analyze_codebase_classifications_handles_multiple_technologies(mock_codebase_path, mock_anthropic_client):
    """Test identification of multiple technologies in codebase."""
    # Given a codebase with multiple technologies
    mock_anthropic_client.create_message = AsyncMock(return_value="Python, React")
    
    # When analyzing the codebase
    result = await analyze_codebase_classifications(mock_codebase_path, MOCK_CLASSIFICATIONS)
    
    # Then both technologies should be identified
    expected_ids = {MOCK_CLASSIFICATIONS[0].id, MOCK_CLASSIFICATIONS[1].id}  # Python and React IDs
    assert set(result) == expected_ids

async def test_analyze_codebase_classifications_handles_no_matches(mock_codebase_path, mock_anthropic_client):
    """Test handling when no technologies are identified."""
    # Given a codebase with no matching technologies
    mock_anthropic_client.create_message = AsyncMock(return_value="")
    
    # When analyzing the codebase
    result = await analyze_codebase_classifications(mock_codebase_path, MOCK_CLASSIFICATIONS)
    
    # Then an empty list should be returned
    assert result == []

async def test_analyze_codebase_classifications_handles_invalid_path():
    """Test error handling for invalid codebase path."""
    # Given an invalid codebase path
    # When analyzing the codebase
    with pytest.raises(ClassificationError) as exc_info:
        await analyze_codebase_classifications(Path("/invalid/path"), MOCK_CLASSIFICATIONS)
    
    # Then a ClassificationError should be raised
    assert "Classification analysis failed" in str(exc_info.value)

async def test_analyze_codebase_classifications_handles_llm_error(mock_codebase_path, mock_anthropic_client):
    """Test error handling when LLM fails."""
    # Given a failing LLM client
    mock_anthropic_client.create_message = AsyncMock(side_effect=Exception("LLM Error"))
    
    # When analyzing the codebase
    with pytest.raises(ClassificationError) as exc_info:
        await analyze_codebase_classifications(mock_codebase_path, MOCK_CLASSIFICATIONS)
    
    # Then a ClassificationError should be raised
    assert "Classification analysis failed" in str(exc_info.value)

async def test_analyze_codebase_classifications_handles_binary_files(mock_codebase_path, mock_anthropic_client):
    """Test handling of binary files in codebase."""
    # Given a codebase with binary files
    binary_file = mock_codebase_path / "test.jpg"
    binary_file.write_bytes(b"binary content")
    
    # When analyzing the codebase
    result = await analyze_codebase_classifications(mock_codebase_path, MOCK_CLASSIFICATIONS)
    
    # Then classification should succeed ignoring binary files
    assert result == [MOCK_CLASSIFICATIONS[0].id]  # Python classification ID

@patch('builtins.open')
async def test_analyze_codebase_classifications_handles_unicode_decode_error(mock_open_func, mock_codebase_path, mock_anthropic_client):
    """Test handling of UnicodeDecodeError when reading files."""
    # Given a file that raises UnicodeDecodeError
    mock_open_func.side_effect = [
        mock_open(read_data=MOCK_CODEBASE_CONTENT).return_value,  # First file opens fine
        UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')  # Second file fails
    ]
    
    # When analyzing the codebase
    result = await analyze_codebase_classifications(mock_codebase_path, MOCK_CLASSIFICATIONS)
    
    # Then analysis should succeed with readable files
    assert result == [MOCK_CLASSIFICATIONS[0].id]

async def test_analyze_codebase_classifications_handles_malformed_llm_response(mock_codebase_path, mock_anthropic_client):
    """Test handling of malformed LLM response."""
    # Given an LLM that returns a malformed response
    mock_anthropic_client.create_message = AsyncMock(return_value="Invalid\nResponse\nFormat")
    
    # When analyzing the codebase
    result = await analyze_codebase_classifications(mock_codebase_path, MOCK_CLASSIFICATIONS)
    
    # Then an empty list should be returned (no valid classifications found)
    assert result == []

async def test_analyze_codebase_classifications_handles_empty_codebase(mock_codebase_path, mock_anthropic_client):
    """Test handling of empty codebase directory."""
    # Given an empty codebase directory
    for file in mock_codebase_path.iterdir():
        file.unlink()
    mock_anthropic_client.create_message = AsyncMock(return_value="")  # Empty response for empty codebase
    
    # When analyzing the codebase
    result = await analyze_codebase_classifications(mock_codebase_path, MOCK_CLASSIFICATIONS)
    
    # Then an empty list should be returned
    assert result == [] 