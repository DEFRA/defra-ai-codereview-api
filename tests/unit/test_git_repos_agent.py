"""Unit tests for git_repos_agent.py."""
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
    """Create a temporary directory for testing."""
    return tmp_path

@pytest.fixture
def mock_repo_structure(mock_temp_dir):
    """Create a mock repository structure for testing."""
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
    """Test flatten_repository function."""
    output_file = tmp_path / "output.txt"
    
    await flatten_repository(mock_repo_structure, output_file)
    
    # Check output file exists and contains expected content
    assert output_file.exists()
    content = output_file.read_text()
    assert "test.py" in content
    assert "print('test')" in content
    assert "test.png" not in content
    assert "node_modules" not in content

@pytest.mark.asyncio
async def test_flatten_repository_error_handling(mock_repo_structure, tmp_path):
    """Test flatten_repository error handling for unreadable files."""
    output_file = tmp_path / "output.txt"
    
    # Create a file that will raise UnicodeDecodeError
    binary_file = mock_repo_structure / "binary.dat"
    with open(binary_file, 'wb') as f:
        f.write(b'\x80\x81')
    
    await flatten_repository(mock_repo_structure, output_file)
    
    # Check output file exists and contains expected content
    assert output_file.exists()
    content = output_file.read_text()
    assert b'\x80\x81' not in content.encode('utf-8')

@pytest.mark.asyncio
async def test_process_standards_repo_llm_testing(mock_temp_dir):
    """Test process_standards_repo with LLM testing enabled."""
    with patch('src.agents.git_repos_agent.settings') as mock_settings:
        mock_settings.LLM_TESTING = True
        mock_settings.LLM_TESTING_STANDARDS_FILES = "test1,test2"
        
        result = await process_standards_repo(mock_temp_dir)
        
        assert len(result) == 2
        assert all(isinstance(path, Path) for path in result)
        assert all("test" in str(path) for path in result)

@pytest.mark.asyncio
async def test_process_standards_repo_normal(mock_temp_dir):
    """Test process_standards_repo with actual files."""
    with patch('src.agents.git_repos_agent.settings') as mock_settings:
        mock_settings.LLM_TESTING = False
        
        # Create mock standards files
        principles_file = mock_temp_dir / "test_principles.md"
        principles_file.write_text("Test principles")
        
        standards_file = mock_temp_dir / "test_standards.md"
        standards_file.write_text("Test standards")
        
        result = await process_standards_repo(mock_temp_dir)
        
        assert len(result) == 2
        assert all(isinstance(path, Path) for path in result)
        assert any("principles" in str(path) for path in result)
        assert any("standards" in str(path) for path in result)

@pytest.mark.asyncio
async def test_process_standards_repo_error_handling(mock_temp_dir):
    """Test process_standards_repo error handling for unreadable files."""
    with patch('src.agents.git_repos_agent.settings') as mock_settings:
        mock_settings.LLM_TESTING = False
        
        # Create a standards file that will raise UnicodeDecodeError
        standards_file = mock_temp_dir / "test_standards.md"
        with open(standards_file, 'wb') as f:
            f.write(b'\x80\x81')
        
        result = await process_standards_repo(mock_temp_dir)
        assert len(result) == 0

@pytest.mark.asyncio
async def test_clone_repo():
    """Test clone_repo function."""
    with patch('git.Repo.clone_from') as mock_clone:
        target_dir = Path("test_dir")
        repo_url = "https://github.com/test/repo.git"
        
        await clone_repo(repo_url, target_dir)
        
        mock_clone.assert_called_once_with(repo_url, target_dir)

@pytest.mark.asyncio
async def test_clone_repo_existing_directory():
    """Test clone_repo handles existing directory cleanup."""
    with patch('git.Repo.clone_from') as mock_clone, \
         patch('shutil.rmtree') as mock_rmtree:
        target_dir = Path("test_dir")
        repo_url = "https://github.com/test/repo.git"
        
        # Create a mock directory that exists
        with patch.object(Path, 'exists', return_value=True):
            await clone_repo(repo_url, target_dir)
            
            mock_rmtree.assert_called_once_with(target_dir)
            mock_clone.assert_called_once_with(repo_url, target_dir)

@pytest.mark.asyncio
async def test_process_repositories():
    """Test process_repositories function."""
    repo_url = "https://github.com/test/repo.git"
    
    with patch('src.agents.git_repos_agent.clone_repo') as mock_clone, \
         patch('src.agents.git_repos_agent.flatten_repository') as mock_flatten, \
         patch('src.agents.git_repos_agent.process_standards_repo') as mock_process_standards, \
         patch('tempfile.TemporaryDirectory') as mock_temp_dir:
        
        # Setup mocks
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test"
        mock_process_standards.return_value = [Path("test_standard.txt")]
        
        codebase_file, standards_files = await process_repositories(repo_url)
        
        # Verify calls
        assert mock_clone.call_count == 2
        assert mock_clone.call_args_list[0][0][0] == repo_url
        assert mock_clone.call_args_list[1][0][0] == STANDARDS_REPO
        
        assert mock_flatten.called
        assert mock_process_standards.called
        
        assert isinstance(codebase_file, Path)
        assert isinstance(standards_files, list)
        assert len(standards_files) == 1 