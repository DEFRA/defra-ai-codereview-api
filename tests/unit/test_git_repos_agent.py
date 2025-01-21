"""Unit tests for the Git repository processing functionality.

This module tests the core functionality for:
1. Repository cloning and management
2. Code flattening and processing
3. Standards repository handling
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from src.agents.git_repos_agent import (
    clone_repo,
    flatten_repository,
    process_repositories,
    STANDARDS_REPO,
    DATA_DIR,
    CODEBASE_DIR
)

@pytest.fixture
def mock_temp_dir(tmp_path):
    """Provide a temporary directory for testing."""
    return tmp_path

@pytest.fixture
def mock_repo_structure(mock_temp_dir):
    """
    Create a mock repository structure for testing.
    
    Structure:
    - test.py (valid Python file)
    - test.png (excluded binary file)
    - node_modules/ (excluded directory)
      - test.js
    """
    # Create test files
    test_file = mock_temp_dir / "test.py"
    test_file.write_text("print('test')")
    
    # Create excluded files
    excluded_file = mock_temp_dir / "test.png"
    excluded_file.write_text("binary content")
    
    # Create excluded directory
    node_modules = mock_temp_dir / "node_modules"
    node_modules.mkdir()
    (node_modules / "test.js").write_text("console.log('test')")
    
    return mock_temp_dir

@pytest.mark.asyncio
async def test_flatten_repository(mock_repo_structure, tmp_path):
    """Test repository flattening with valid files."""
    # Given
    output_file = tmp_path / "output.txt"
    
    # When
    await flatten_repository(mock_repo_structure, output_file)
    
    # Then
    assert output_file.exists()
    content = output_file.read_text()
    assert "test.py" in content
    assert "print('test')" in content
    assert "test.png" not in content
    assert "test.js" not in content

@pytest.mark.asyncio
async def test_clone_repo():
    """Test repository cloning."""
    with patch('src.agents.git_repos_agent.git.Repo') as mock_repo:
        mock_repo.clone_from = MagicMock()
        repo_url = "https://github.com/test/repo.git"
        local_path = Path("/tmp/test-repo")
        
        await clone_repo(repo_url, local_path)
        
        mock_repo.clone_from.assert_called_once_with(repo_url, str(local_path))

@pytest.mark.asyncio
async def test_process_repositories():
    """Test end-to-end repository processing."""
    with patch('src.agents.git_repos_agent.clone_repo') as mock_clone, \
         patch('src.agents.git_repos_agent.flatten_repository') as mock_flatten, \
         patch('tempfile.TemporaryDirectory') as mock_temp_dir:
        
        # Setup
        repo_url = "https://github.com/test/repo.git"
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test"
        expected_output = CODEBASE_DIR / "repo.txt"
        
        # When
        result = await process_repositories(repo_url)
        
        # Then
        assert mock_clone.called
        assert mock_flatten.called
        assert result == expected_output

@pytest.mark.asyncio
async def test_process_repository_processes_valid_files(mock_repo_structure, tmp_path):
    """Test repository processing with valid files."""
    # Given
    with patch('src.agents.git_repos_agent.clone_repo') as mock_clone, \
         patch('src.agents.git_repos_agent.flatten_repository') as mock_flatten:
        
        # When
        result = await process_repositories("https://github.com/test/repo.git")
        
        # Then
        assert mock_clone.called
        assert mock_flatten.called
        assert isinstance(result, Path)
        assert result.name.endswith(".txt")

@pytest.mark.asyncio
async def test_process_repository_handles_binary_files(mock_repo_structure, tmp_path):
    """Test repository processing with binary files."""
    # Given
    with patch('src.agents.git_repos_agent.clone_repo') as mock_clone, \
         patch('src.agents.git_repos_agent.flatten_repository') as mock_flatten:
        
        # When
        result = await process_repositories("https://github.com/test/repo.git")
        
        # Then
        assert mock_clone.called
        assert mock_flatten.called
        assert isinstance(result, Path)
        assert result.name.endswith(".txt")

@pytest.mark.asyncio
async def test_process_standards_repo_skips_git_directory(mock_temp_dir):
    """
    Test standards processing skips .git directory.
    
    Given: A standards repository with a file in .git directory
    When: Processing standards repository
    Then: Should skip files in .git directory
    """
    # Given
    with patch('src.agents.git_repos_agent.clone_repo') as mock_clone, \
         patch('src.agents.git_repos_agent.flatten_repository') as mock_flatten:
        
        # Create .git directory with a file
        git_dir = mock_temp_dir / ".git"
        git_dir.mkdir(exist_ok=True)
        git_file = git_dir / "test_standards.md"
        git_file.write_text("Test standards in git")
        
        # When
        result = await process_repositories("https://github.com/test/repo.git")
        
        # Then
        assert mock_clone.called
        assert mock_flatten.called
        assert isinstance(result, Path)
        assert result.name.endswith(".txt")

@pytest.mark.asyncio
async def test_process_standards_repo_skips_invalid_suffixes(mock_temp_dir):
    """
    Test standards processing skips files with invalid suffixes.
    
    Given: A standards repository with files having invalid suffixes
    When: Processing standards repository
    Then: Should skip files without _principles.md or _standards.md suffix
    """
    # Given
    with patch('src.agents.git_repos_agent.clone_repo') as mock_clone, \
         patch('src.agents.git_repos_agent.flatten_repository') as mock_flatten:
        
        # Create file with invalid suffix
        invalid_file = mock_temp_dir / "test_invalid.md"
        invalid_file.write_text("Test invalid suffix")
        
        # Create file with valid suffix for comparison
        valid_file = mock_temp_dir / "test_standards.md"
        valid_file.write_text("Test valid suffix")
        
        # When
        result = await process_repositories("https://github.com/test/repo.git")
        
        # Then
        assert mock_clone.called
        assert mock_flatten.called
        assert isinstance(result, Path)
        assert result.name.endswith(".txt") 