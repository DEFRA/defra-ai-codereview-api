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
    flatten_repository,
    process_standards_repo,
    clone_repo,
    process_repositories,
    STANDARDS_REPO
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
async def test_flatten_repository_processes_valid_files(mock_repo_structure, tmp_path):
    """
    Test repository flattening with valid files.
    
    Given: A repository with mixed content (valid and excluded files)
    When: Flattening the repository
    Then: Only valid files should be included in output
    """
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
    assert "node_modules" not in content

@pytest.mark.asyncio
async def test_flatten_repository_handles_binary_files(mock_repo_structure, tmp_path):
    """
    Test repository flattening with binary files.
    
    Given: A repository containing a binary file
    When: Flattening the repository
    Then: Binary file should be gracefully skipped
    """
    # Given
    output_file = tmp_path / "output.txt"
    binary_file = mock_repo_structure / "binary.dat"
    with open(binary_file, 'wb') as f:
        f.write(b'\x80\x81')
    
    # When
    await flatten_repository(mock_repo_structure, output_file)
    
    # Then
    assert output_file.exists()
    content = output_file.read_text()
    assert b'\x80\x81' not in content.encode('utf-8')

@pytest.mark.asyncio
async def test_process_standards_repo_in_llm_testing_mode(mock_temp_dir):
    """
    Test standards processing in LLM testing mode.
    
    Given: LLM testing mode is enabled
    When: Processing standards repository
    Then: Should return mock test files
    """
    # Given
    with patch('src.agents.git_repos_agent.settings') as mock_settings:
        mock_settings.LLM_TESTING = True
        mock_settings.LLM_TESTING_STANDARDS_FILES = "test1,test2"
        
        # When
        result = await process_standards_repo(mock_temp_dir)
        
        # Then
        assert len(result) == 2
        assert all(isinstance(path, Path) for path in result)
        assert all("test" in str(path) for path in result)

@pytest.mark.asyncio
async def test_process_standards_repo_with_actual_files(mock_temp_dir):
    """
    Test standards processing with real files.
    
    Given: A standards repository with markdown files
    When: Processing standards repository
    Then: Should return paths to principles and standards files
    """
    # Given
    with patch('src.agents.git_repos_agent.settings') as mock_settings:
        mock_settings.LLM_TESTING = False
        
        principles_file = mock_temp_dir / "test_principles.md"
        principles_file.write_text("Test principles")
        
        standards_file = mock_temp_dir / "test_standards.md"
        standards_file.write_text("Test standards")
        
        # When
        result = await process_standards_repo(mock_temp_dir)
        
        # Then
        assert len(result) == 2
        assert all(isinstance(path, Path) for path in result)
        assert any("principles" in str(path) for path in result)
        assert any("standards" in str(path) for path in result)

@pytest.mark.asyncio
async def test_process_standards_repo_handles_corrupt_files(mock_temp_dir):
    """
    Test standards processing with corrupt files.
    
    Given: A standards repository with a corrupt file
    When: Processing standards repository
    Then: Should gracefully skip corrupt files
    """
    # Given
    with patch('src.agents.git_repos_agent.settings') as mock_settings:
        mock_settings.LLM_TESTING = False
        
        standards_file = mock_temp_dir / "test_standards.md"
        with open(standards_file, 'wb') as f:
            f.write(b'\x80\x81')
        
        # When
        result = await process_standards_repo(mock_temp_dir)
        
        # Then
        assert len(result) == 0

@pytest.mark.asyncio
async def test_process_standards_repo_skips_git_directory(mock_temp_dir):
    """
    Test standards processing skips .git directory.
    
    Given: A standards repository with a file in .git directory
    When: Processing standards repository
    Then: Should skip files in .git directory
    """
    # Given
    with patch('src.agents.git_repos_agent.settings') as mock_settings:
        mock_settings.LLM_TESTING = False
        
        # Create .git directory with a file
        git_dir = mock_temp_dir / ".git"
        git_dir.mkdir()
        git_file = git_dir / "test_standards.md"
        git_file.write_text("Test standards in git")
        
        # When
        result = await process_standards_repo(mock_temp_dir)
        
        # Then
        assert len(result) == 0

@pytest.mark.asyncio
async def test_process_standards_repo_skips_invalid_suffixes(mock_temp_dir):
    """
    Test standards processing skips files with invalid suffixes.
    
    Given: A standards repository with files having invalid suffixes
    When: Processing standards repository
    Then: Should skip files without _principles.md or _standards.md suffix
    """
    # Given
    with patch('src.agents.git_repos_agent.settings') as mock_settings:
        mock_settings.LLM_TESTING = False
        
        # Create file with invalid suffix
        invalid_file = mock_temp_dir / "test_invalid.md"
        invalid_file.write_text("Test invalid suffix")
        
        # Create file with valid suffix for comparison
        valid_file = mock_temp_dir / "test_standards.md"
        valid_file.write_text("Test valid suffix")
        
        # When
        result = await process_standards_repo(mock_temp_dir)
        
        # Then
        assert len(result) == 1
        assert "test_standards.md" in str(result[0])

@pytest.mark.asyncio
async def test_clone_repo_clones_successfully():
    """
    Test successful repository cloning.
    
    Given: A valid repository URL
    When: Cloning the repository
    Then: Should clone to target directory
    """
    # Given
    target_dir = Path("test_dir")
    repo_url = "https://github.com/test/repo.git"
    
    # When
    with patch('git.Repo.clone_from') as mock_clone:
        await clone_repo(repo_url, target_dir)
        
        # Then
        mock_clone.assert_called_once_with(repo_url, target_dir)

@pytest.mark.asyncio
async def test_clone_repo_handles_existing_directory():
    """
    Test cloning when target directory exists.
    
    Given: A target directory that already exists
    When: Cloning the repository
    Then: Should clean up existing directory before cloning
    """
    # Given
    target_dir = Path("test_dir")
    repo_url = "https://github.com/test/repo.git"
    
    # When
    with patch('git.Repo.clone_from') as mock_clone, \
         patch('shutil.rmtree') as mock_rmtree, \
         patch.object(Path, 'exists', return_value=True):
        await clone_repo(repo_url, target_dir)
        
        # Then
        mock_rmtree.assert_called_once_with(target_dir)
        mock_clone.assert_called_once_with(repo_url, target_dir)

@pytest.mark.asyncio
async def test_process_repositories_end_to_end():
    """
    Test complete repository processing flow.
    
    Given: A repository URL to process
    When: Processing both code and standards repositories
    Then: Should return flattened code and standards files
    """
    # Given
    repo_url = "https://github.com/test/repo.git"
    
    # When
    with patch('src.agents.git_repos_agent.clone_repo') as mock_clone, \
         patch('src.agents.git_repos_agent.flatten_repository') as mock_flatten, \
         patch('src.agents.git_repos_agent.process_standards_repo') as mock_process_standards, \
         patch('tempfile.TemporaryDirectory') as mock_temp_dir:
        
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test"
        mock_process_standards.return_value = [Path("test_standard.txt")]
        
        codebase_file, standards_files = await process_repositories(repo_url)
        
        # Then
        assert mock_clone.call_count == 2
        assert mock_clone.call_args_list[0][0][0] == repo_url
        assert mock_clone.call_args_list[1][0][0] == STANDARDS_REPO
        
        assert mock_flatten.called
        assert mock_process_standards.called
        
        assert isinstance(codebase_file, Path)
        assert isinstance(standards_files, list)
        assert len(standards_files) == 1 