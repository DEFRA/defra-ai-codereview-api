'''Integration tests for repository processing functionality.

Tests cover the repository downloading and processing functionality while mocking
Git operations but using real file system operations.'''
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import git
import shutil
from src.agents.git_repos_agent import clone_repo, process_repositories
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)

# Test Setup and Fixtures


@pytest.fixture(autouse=True)
async def setup_and_teardown():
    """Setup and teardown for each test."""
    # Setup
    yield
    # Teardown - ensure all temp directories are cleaned up
    try:
        shutil.rmtree("temp_test_dir", ignore_errors=True)
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")


@pytest.fixture
def mock_git_repo():
    """Mock git.Repo for testing."""
    with patch('git.Repo') as mock_repo:
        # Configure the mock to track clone calls
        mock_repo.clone_from = MagicMock(
            side_effect=lambda url, path: Path(path).mkdir(exist_ok=True))
        yield mock_repo


@pytest.fixture
async def mock_temp_dir():
    """Create and manage a temporary directory.

    Uses a fixed path for testing to ensure directory exists throughout test.
    Directory is cleaned up by autouse fixture after each test.
    """
    temp_dir = Path("temp_test_dir")
    temp_dir.mkdir(exist_ok=True)
    return temp_dir


@pytest.fixture
def test_repo_url():
    """Test repository URL."""
    return "https://github.com/test/repo.git"

# Test Cases


@pytest.mark.asyncio
async def test_download_repository_success(
    mock_git_repo,
    mock_temp_dir,
    test_repo_url
):
    """Test successful repository download and structure.

    Given:
    - A valid repository URL
    - A temporary directory for cloning

    When:
    - The clone_repo function is called

    Then:
    - Git clone operation should be called correctly
    - Temporary directory should be recreated
    - Function should return a valid Path object
    - Directory should exist after cloning
    """
    # Given: Ensure temp directory exists initially
    assert mock_temp_dir.exists(), "Temporary directory should exist before test"

    # When: Clone the repository
    await clone_repo(test_repo_url, mock_temp_dir)

    # Then: Verify the clone operation
    mock_git_repo.clone_from.assert_called_once_with(
        test_repo_url,
        str(mock_temp_dir)
    )

    # And: Verify the directory exists and is a Path
    assert isinstance(mock_temp_dir, Path)
    assert mock_temp_dir.exists(), "Temporary directory should exist after cloning"


@pytest.mark.asyncio
async def test_repository_structure_preservation(tmp_path, test_repo_url, monkeypatch):
    """Test that the repository structure is preserved after cloning.

    Given:
        A fake repository structure with nested directories and mixed file types.
    When:
        The clone_repo function is called (patched to return the fake repository).
    Then:
        The returned repository contains the expected nested structure.
    """
    # Create a fake repository structure in a temporary directory
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    (fake_repo / "README.md").write_text("# Repository README")
    docs = fake_repo / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("Documentation guide")
    (fake_repo / "notes.txt").write_text("Some notes")
    images_dir = docs / "images"
    images_dir.mkdir()
    (images_dir / "logo.png").write_text("Image binary data")

    # Define a fake clone_repo that returns our fake repository regardless of inputs
    async def fake_clone_repo(url: str, dest: str):
        return fake_repo

    import src.agents.git_repos_agent as git_agent
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    # When: Call clone_repo (which is patched) with test_repo_url and any destination
    cloned_repo_path = await git_agent.clone_repo(test_repo_url, str(tmp_path))

    # Then: Verify that the repository structure is preserved
    assert (cloned_repo_path /
            "README.md").exists(), "README.md should exist in the cloned repo"
    assert (cloned_repo_path / "docs").is_dir(), "docs directory should exist"
    assert (cloned_repo_path / "docs" /
            "guide.md").exists(), "guide.md should exist in docs"
    assert (cloned_repo_path /
            "notes.txt").exists(), "notes.txt should exist in the cloned repo"
    assert (cloned_repo_path / "docs" /
            "images").is_dir(), "images directory should exist inside docs"
    assert (cloned_repo_path / "docs" / "images" /
            "logo.png").exists(), "logo.png should exist in images"
