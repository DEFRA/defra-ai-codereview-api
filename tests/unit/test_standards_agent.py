"""Unit tests for the standards agent functionality.

This module tests the core functionality for:
1. Processing standard sets
2. Downloading and managing repositories
3. Analyzing standards with LLM
4. Error handling
"""
import os
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from anthropic import Anthropic
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.agents.standards_agent import (
    process_standard_set,
    download_repository,
    get_classifications,
    cleanup_repository,
    process_standards,
    analyze_standard
)
from src.models.classification import Classification
from src.repositories.classification_repo import ClassificationRepository

@pytest.fixture
def mock_db():
    """Provide a mock database."""
    mock = AsyncMock(spec=AsyncIOMotorDatabase)
    mock.get_collection = MagicMock(return_value=AsyncMock())
    return mock

@pytest.fixture
def mock_classifications():
    """Provide mock classifications."""
    return [
        Classification(id=ObjectId(), name="Python"),
        Classification(id=ObjectId(), name="Docker")
    ]

@pytest.fixture
def mock_repo_path(tmp_path):
    """Provide a temporary directory for repo operations."""
    return tmp_path / "test_repo"

@pytest.mark.asyncio
async def test_download_repository():
    """Test repository download functionality."""
    with patch('src.agents.standards_agent.clone_repo') as mock_clone:
        repo_url = "https://example.com/repo.git"
        result = await download_repository(repo_url)
        assert mock_clone.called
        assert isinstance(result, Path)

@pytest.mark.asyncio
async def test_get_classifications(mock_db):
    """Test retrieving classifications."""
    # Setup
    mock_classifications = [
        {"_id": ObjectId(), "name": "Python"},
        {"_id": ObjectId(), "name": "Docker"}
    ]
    
    # Create a mock cursor that supports async iteration
    class MockCursor:
        def __init__(self, items):
            self.items = items.copy()
            
        def __aiter__(self):
            return self
            
        async def __anext__(self):
            if not self.items:
                raise StopAsyncIteration
            return self.items.pop(0)
    
    # Mock the collection's find method to return our cursor
    mock_collection = AsyncMock()
    mock_collection.find = MagicMock(return_value=MockCursor(mock_classifications))
    mock_db.get_collection.return_value = mock_collection
    
    # Execute
    result = await get_classifications(mock_db)
    
    # Verify
    assert len(result) == 2
    assert mock_db.get_collection.called
    assert all(isinstance(c, Classification) for c in result)

def test_cleanup_repository(mock_repo_path):
    """Test repository cleanup."""
    mock_repo_path.mkdir(parents=True)
    (mock_repo_path / "test.txt").touch()
    
    cleanup_repository(mock_repo_path)
    assert not mock_repo_path.exists()

@pytest.mark.asyncio
async def test_process_standards_llm_testing_mode(mock_db, mock_classifications, mock_repo_path):
    """Test processing standards in LLM testing mode."""
    # Setup
    mock_repo_path.mkdir()
    test_file = mock_repo_path / "coding_principles.md"  # Use a valid test file name
    test_file.write_text("# Test Standard")
    
    standard_set_id = str(ObjectId())
    
    # Mock analyze_standard to return some classifications
    mock_analyze = AsyncMock(return_value=["Python"])
    
    # Mock collection operations
    mock_collection = AsyncMock()
    mock_collection.delete_many = AsyncMock()
    mock_collection.insert_one = AsyncMock()
    mock_db.get_collection.return_value = mock_collection
    
    with patch.dict('os.environ', {'LLM_TESTING': 'true', 'LLM_TESTING_STANDARDS_FILES': 'coding_principles.md'}), \
         patch('src.agents.standards_agent.analyze_standard', mock_analyze), \
         patch('src.config.settings') as mock_settings:
        # Configure settings
        mock_llm_testing = PropertyMock(return_value=True)
        mock_llm_files = PropertyMock(return_value="coding_principles.md")
        type(mock_settings).LLM_TESTING = mock_llm_testing
        type(mock_settings).LLM_TESTING_STANDARDS_FILES = mock_llm_files
        
        # Execute
        await process_standards(mock_db, mock_repo_path, standard_set_id, mock_classifications)
        
        # Verify
        assert mock_collection.delete_many.called
        assert mock_collection.insert_one.called

@pytest.mark.asyncio
async def test_process_standards_non_llm_mode(mock_db, mock_classifications, mock_repo_path):
    """Test processing standards in non-LLM mode."""
    # Setup
    mock_repo_path.mkdir()
    test_file = mock_repo_path / "test.md"
    test_file.write_text("# Test Standard")
    
    standard_set_id = str(ObjectId())
    
    # Mock analyze_standard to return some classifications
    mock_analyze = AsyncMock(return_value=["Python"])
    
    # Mock collection operations
    mock_collection = AsyncMock()
    mock_collection.delete_many = AsyncMock()
    mock_collection.insert_one = AsyncMock()
    mock_db.get_collection.return_value = mock_collection
    
    # Create a mock settings object
    class MockSettings:
        @property
        def LLM_TESTING(self):
            return False
            
        @property
        def LLM_TESTING_STANDARDS_FILES(self):
            return ""
    
    mock_settings = MockSettings()
    
    with patch.dict('os.environ', {'LLM_TESTING': 'false'}, clear=True), \
         patch('src.agents.standards_agent.analyze_standard', mock_analyze), \
         patch('src.agents.standards_agent.settings', mock_settings):
        # Execute
        await process_standards(mock_db, mock_repo_path, standard_set_id, mock_classifications)
        
        # Verify
        assert mock_collection.delete_many.called
        assert mock_collection.insert_one.called

@pytest.mark.asyncio
async def test_analyze_standard_universal(mock_classifications):
    """Test analyzing a universal standard."""
    # Setup
    content = """# Security Standard
## Requirements
- Use HTTPS
- Encrypt sensitive data
"""
    classifications = [c.name for c in mock_classifications]
    
    # Create a mock message with empty response
    class MockContent:
        def __init__(self, text):
            self.text = text
            
        def strip(self):
            return self.text
    
    mock_message = MagicMock()
    mock_message.content = [MockContent("")]
    
    # Create a mock client
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    
    # Execute
    with patch('src.agents.standards_agent.Anthropic', return_value=mock_client), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        result = await analyze_standard(content, classifications)
        
        # Verify
        assert result == []
        assert mock_client.messages.create.called

@pytest.mark.asyncio
async def test_analyze_standard_specific_classifications(mock_classifications):
    """Test analyzing a standard with specific classifications."""
    # Setup
    content = """# Python Testing Standard
## Requirements
- Use pytest
- Write unit tests
"""
    classifications = [c.name for c in mock_classifications]
    
    # Create a mock message with Python classification
    class MockContent:
        def __init__(self, text):
            self.text = text
            
        def strip(self):
            return self.text
    
    mock_message = MagicMock()
    mock_message.content = [MockContent("Python")]
    
    # Create a mock client that returns the message directly
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    
    # Execute
    with patch('src.agents.standards_agent.Anthropic', return_value=mock_client), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        result = await analyze_standard(content, classifications)
        
        # Verify
        assert result == ["Python"]
        assert mock_client.messages.create.called

@pytest.mark.asyncio
async def test_analyze_standard_handles_llm_error():
    """Test error handling in standard analysis."""
    # Setup
    content = "Test content"
    classifications = ["Python"]
    
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))
    
    # Execute
    with patch('src.agents.standards_agent.Anthropic', return_value=mock_client), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'}):
        result = await analyze_standard(content, classifications)
        
        # Verify
        assert result == []
        assert mock_client.messages.create.called

@pytest.mark.asyncio
async def test_process_standards_handles_file_error(mock_db, mock_classifications, mock_repo_path):
    """Test handling of file processing errors."""
    # Setup
    mock_repo_path.mkdir()
    test_file = mock_repo_path / "test_standard.md"
    test_file.write_text("# Test Standard")
    
    standard_set_id = str(ObjectId())
    
    # Mock collection operations
    mock_collection = AsyncMock()
    mock_collection.delete_many = AsyncMock()
    mock_collection.insert_one = AsyncMock()
    mock_db.get_collection.return_value = mock_collection
    
    with patch('builtins.open', side_effect=Exception("File error")):
        # Execute
        await process_standards(mock_db, mock_repo_path, standard_set_id, mock_classifications)
        
        # Verify
        assert mock_collection.delete_many.called
        assert not mock_collection.insert_one.called

@pytest.mark.asyncio
async def test_process_standard_set_handles_error(mock_db):
    """Test error handling in process_standard_set."""
    # Setup
    standard_set_id = str(ObjectId())
    repository_url = "https://example.com/repo.git"
    
    with patch('src.agents.standards_agent.download_repository', side_effect=Exception("Clone error")), \
         patch('src.database.get_database', return_value=mock_db):
        # Execute
        await process_standard_set(standard_set_id, repository_url)
        
        # Verify no exceptions are raised
        pass

@pytest.mark.asyncio
async def test_process_standard_set_success(mock_db, mock_repo_path):
    """Test successful standard set processing."""
    # Setup
    standard_set_id = str(ObjectId())
    repository_url = "https://example.com/repo.git"
    
    mock_download = AsyncMock(return_value=mock_repo_path)
    mock_classifications = [
        Classification(id=ObjectId(), name="Python"),
        Classification(id=ObjectId(), name="Docker")
    ]
    mock_get_classifications = AsyncMock(return_value=mock_classifications)
    
    with patch('src.agents.standards_agent.download_repository', mock_download), \
         patch('src.agents.standards_agent.get_classifications', mock_get_classifications), \
         patch('src.agents.standards_agent.process_standards') as mock_process, \
         patch('src.agents.standards_agent.cleanup_repository') as mock_cleanup, \
         patch('src.database.get_database', return_value=mock_db):
        # Execute
        await process_standard_set(standard_set_id, repository_url)
        
        # Verify
        assert mock_download.called
        assert mock_get_classifications.called
        assert mock_process.called
        assert mock_cleanup.called 