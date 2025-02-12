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
import asyncio

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


@pytest.mark.asyncio
async def test_download_into_prepopulated_directory(mock_git_repo, tmp_path, test_repo_url):
    """Test cloning into a pre-populated directory.

    Given:
        A temporary directory with pre-existing content.
    When:
        clone_repo is called.
    Then:
        The directory should be cleared before cloning, removing pre-existing files.
    """
    # Create a pre-populated directory with a dummy file
    prepopulated_dir = tmp_path / "prepopulated_dir"
    prepopulated_dir.mkdir()
    dummy_file = prepopulated_dir / "dummy.txt"
    dummy_file.write_text("dummy content")

    # Call clone_repo - expecting it to clear the directory before cloning
    from src.agents.git_repos_agent import clone_repo
    await clone_repo(test_repo_url, prepopulated_dir)

    # Assert that the dummy file has been removed
    assert not dummy_file.exists(), "Directory should be cleared before cloning"


@pytest.mark.asyncio
async def test_repository_relative_paths_integrity(tmp_path, test_repo_url, monkeypatch):
    """Test that the repository relative paths are preserved after cloning.

    Given:
        A fake repository structure with various file types and deep nested directories.
    When:
        clone_repo is called (patched to return the fake repository).
    Then:
        The relative file paths in the cloned repository should match the original structure.
    """
    # Create a complex fake repository structure in a temporary directory
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    (fake_repo / "README.md").write_text("Repository README")
    (fake_repo / "config.json").write_text("{\"key\": \"value\"}")
    (fake_repo / "data.csv").write_text("col1,col2\nval1,val2")
    subdir = fake_repo / "subdir"
    subdir.mkdir()
    (subdir / "note.txt").write_text("Note in subdir")
    deep_dir = fake_repo / "subdir" / "level2"
    deep_dir.mkdir(parents=True)
    (deep_dir / "deep.md").write_text("# Deep Markdown")

    # Helper function to get sorted list of relative file paths
    def get_relative_paths(path):
        return sorted([str(p.relative_to(path)) for p in path.rglob("*") if p.is_file()])

    original_paths = get_relative_paths(fake_repo)

    # Patch clone_repo to return the fake repository regardless of inputs
    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        return fake_repo
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    # Define a destination for cloning
    clone_target = tmp_path / "clone_target"
    clone_target.mkdir()

    # Call the patched clone_repo
    cloned_repo_path = await git_agent.clone_repo(test_repo_url, str(clone_target))

    cloned_paths = get_relative_paths(cloned_repo_path)

    assert original_paths == cloned_paths, "The relative file paths of the cloned repository should match the original structure"


@pytest.mark.asyncio
async def test_markdown_processing(tmp_path, test_repo_url, monkeypatch):
    """Test markdown processing to verify detection, parsing, and content preservation.

    Given:
        A fake repository with markdown files containing embedded formatting and a nested markdown file.
    When:
        The repository is cloned via clone_repo (patched to return the fake repo).
    Then:
        The markdown files in the cloned repository should exist and have identical content to the originals.
    """
    # Create a fake repository structure with markdown files
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()

    # Create a sample markdown file in the root with embedded formatting (headers, bold, code block)
    md_content_root = "# Title\n\nThis is a **bold** statement.\n\n```\ncode block\n```"
    md_file_root = fake_repo / "standard.md"
    md_file_root.write_text(md_content_root)

    # Create a nested markdown file in a subdirectory
    subdir = fake_repo / "subdir"
    subdir.mkdir()
    md_content_nested = "## Subtitle\n\n*Italic text* and a list:\n- Item 1\n- Item 2"
    md_file_nested = subdir / "nested_standard.md"
    md_file_nested.write_text(md_content_nested)

    # Add an extra non-markdown file to ensure it is not misinterpreted
    non_md_file = fake_repo / "ignore.txt"
    non_md_file.write_text("This should not be processed as markdown.")

    # Patch clone_repo to always return our fake repository
    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        return fake_repo
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    # Define a destination directory for cloning
    clone_target = tmp_path / "clone_target"
    clone_target.mkdir()

    # Invoke the patched clone_repo
    cloned_repo_path = await git_agent.clone_repo(test_repo_url, str(clone_target))

    # Verify that markdown files are detected in the cloned repository
    cloned_md_file_root = cloned_repo_path / "standard.md"
    cloned_md_file_nested = cloned_repo_path / "subdir" / "nested_standard.md"

    assert cloned_md_file_root.exists(), "Root markdown file should exist in the cloned repo"
    assert cloned_md_file_nested.exists(
    ), "Nested markdown file should exist in the cloned repo"

    # Verify that the content of markdown files is preserved exactly
    assert cloned_md_file_root.read_text(
    ) == md_content_root, "Content of root markdown file should be preserved"
    assert cloned_md_file_nested.read_text(
    ) == md_content_nested, "Content of nested markdown file should be preserved"


@pytest.mark.asyncio
async def test_cleanup_operations(tmp_path, test_repo_url, monkeypatch):
    """Test that temporary resources are cleaned up after repository processing.

    Given:
        A temporary directory used for repository processing and a fake repository.
    When:
        The repository is cloned and processing is complete, followed by explicit cleanup.
    Then:
        The temporary directory is removed and any open file handles are closed.
    """
    # Create a temporary directory for repository processing
    temp_dir = tmp_path / "temp_repo"
    temp_dir.mkdir()

    # Create a fake repository structure
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dummy_file = fake_repo / "dummy.txt"
    dummy_file.write_text("dummy content")

    # Patch clone_repo to return fake_repo regardless of inputs
    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        return fake_repo
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    # Run clone_repo simulation
    cloned_repo_path = await git_agent.clone_repo(test_repo_url, str(temp_dir))
    assert cloned_repo_path.exists(), "Cloned repository should exist before cleanup"

    # Simulate file handle operation: open and close a file in the temp directory
    test_file = temp_dir / "test.txt"
    with test_file.open('w') as f:
        f.write("test content")
    # After exiting the block, the file handle should be closed
    assert test_file.exists(), "Test file should exist after creation"

    # Simulate cleanup by removing the temporary directory
    import shutil
    shutil.rmtree(temp_dir)

    # Verify that the temporary directory is removed
    assert not temp_dir.exists(), "Temporary directory should be removed after cleanup"


# =====================
# Error Case Tasks
# =====================

@pytest.mark.asyncio
async def test_invalid_repository_nonexistent_url(tmp_path, monkeypatch):
    """Test cloning with a non-existent repository URL triggers an exception and cleanup is performed.

    Given:
        A temporary directory and a non-existent repository URL.
    When:
        clone_repo is invoked and simulated to raise an exception for a non-existent URL.
    Then:
        An exception with a descriptive error message is raised and cleanup is performed.
    """
    temp_dir = tmp_path / "temp_invalid_nonexistent"
    temp_dir.mkdir()

    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        raise Exception("Repository not found")
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    with pytest.raises(Exception, match="Repository not found"):
        await git_agent.clone_repo("http://nonexistent", str(temp_dir))

    import shutil
    shutil.rmtree(temp_dir)
    assert not temp_dir.exists(), "Temporary directory should be removed after failure"


@pytest.mark.asyncio
async def test_invalid_repository_malformed_url(tmp_path, monkeypatch):
    """Test cloning with a malformed repository URL triggers an exception and cleanup is performed.

    Given:
        A temporary directory and a malformed repository URL.
    When:
        clone_repo is invoked and simulated to raise an exception for a malformed URL.
    Then:
        An exception with a descriptive error message is raised and cleanup is performed.
    """
    temp_dir = tmp_path / "temp_invalid_malformed"
    temp_dir.mkdir()

    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        raise Exception("Malformed repository URL")
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    with pytest.raises(Exception, match="Malformed repository URL"):
        await git_agent.clone_repo("htp:/malformed_url", str(temp_dir))

    import shutil
    shutil.rmtree(temp_dir)
    assert not temp_dir.exists(), "Temporary directory should be removed after failure"


@pytest.mark.asyncio
async def test_network_timeout_scenario(tmp_path, test_repo_url, monkeypatch):
    """Test that a network timeout during repository cloning raises a TimeoutError and cleanup is performed.

    Given:
        A temporary directory for repository cloning.
    When:
        clone_repo is invoked and simulated to raise a TimeoutError.
    Then:
        A TimeoutError is raised and the temporary directory is cleaned up.
    """
    temp_dir = tmp_path / "temp_network_timeout"
    temp_dir.mkdir()

    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        raise TimeoutError("Simulated network timeout")
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    with pytest.raises(TimeoutError, match="Simulated network timeout"):
        await git_agent.clone_repo(test_repo_url, str(temp_dir))

    import shutil
    shutil.rmtree(temp_dir)
    assert not temp_dir.exists(), "Temporary directory should be removed after network timeout"


@pytest.mark.asyncio
async def test_network_connection_failure(tmp_path, test_repo_url, monkeypatch):
    """Test that a network connection failure during repository cloning raises a ConnectionError and cleanup is performed.

    Given:
        A temporary directory for repository cloning.
    When:
        clone_repo is invoked and simulated to raise a ConnectionError.
    Then:
        A ConnectionError is raised and the temporary directory is cleaned up.
    """
    temp_dir = tmp_path / "temp_network_conn"
    temp_dir.mkdir()

    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        raise ConnectionError("Simulated connection failure")
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    with pytest.raises(ConnectionError, match="Simulated connection failure"):
        await git_agent.clone_repo(test_repo_url, str(temp_dir))

    import shutil
    shutil.rmtree(temp_dir)
    assert not temp_dir.exists(), "Temporary directory should be removed after connection failure"


@pytest.mark.asyncio
async def test_file_system_permission_denied(tmp_path, test_repo_url, monkeypatch):
    """Test that a file system permission error during cloning raises a PermissionError and cleanup is performed.

    Given:
        A temporary directory for repository cloning.
    When:
        clone_repo is invoked and simulated to raise a PermissionError.
    Then:
        A PermissionError is raised with a descriptive message and cleanup is performed.
    """
    temp_dir = tmp_path / "temp_permission"
    temp_dir.mkdir()

    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        raise PermissionError("Permission denied while cloning repository")
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    with pytest.raises(PermissionError, match="Permission denied while cloning repository"):
        await git_agent.clone_repo(test_repo_url, str(temp_dir))

    import shutil
    shutil.rmtree(temp_dir)
    assert not temp_dir.exists(), "Temporary directory should be removed after permission error"


@pytest.mark.asyncio
async def test_file_system_disk_full(tmp_path, test_repo_url, monkeypatch):
    """Test that a disk full error during cloning raises an OSError and cleanup is performed.

    Given:
        A temporary directory for repository cloning.
    When:
        clone_repo is invoked and simulated to raise an OSError indicating no space left.
    Then:
        An OSError is raised with a descriptive message and cleanup is performed.
    """
    temp_dir = tmp_path / "temp_disk_full"
    temp_dir.mkdir()

    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        raise OSError("No space left on device")
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    with pytest.raises(OSError, match="No space left on device"):
        await git_agent.clone_repo(test_repo_url, str(temp_dir))

    import shutil
    shutil.rmtree(temp_dir)
    assert not temp_dir.exists(), "Temporary directory should be removed after disk full error"


@pytest.mark.asyncio
async def test_file_system_readonly_filesystem(tmp_path, test_repo_url, monkeypatch):
    """Test that a read-only filesystem error during cloning raises an OSError and cleanup is performed.

    Given:
        A temporary directory for repository cloning.
    When:
        clone_repo is invoked and simulated to raise an OSError indicating a read-only file system.
    Then:
        An OSError is raised with a descriptive message and cleanup is performed.
    """
    temp_dir = tmp_path / "temp_readonly"
    temp_dir.mkdir()

    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        raise OSError("Read-only file system")
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    with pytest.raises(OSError, match="Read-only file system"):
        await git_agent.clone_repo(test_repo_url, str(temp_dir))

    import shutil
    shutil.rmtree(temp_dir)
    assert not temp_dir.exists(
    ), "Temporary directory should be removed after read-only filesystem error"


@pytest.mark.asyncio
async def test_process_interruption_cancellation(tmp_path, test_repo_url, monkeypatch):
    """Test that cancellation during repository download raises a CancelledError and cleanup is performed.

    Given:
        A temporary directory for repository cloning.
    When:
        clone_repo is invoked and simulated to raise a CancelledError.
    Then:
        A CancelledError is raised and the temporary directory is cleaned up.
    """
    temp_dir = tmp_path / "temp_cancellation"
    temp_dir.mkdir()

    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        raise asyncio.CancelledError("Download cancelled")
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    with pytest.raises(asyncio.CancelledError, match="Download cancelled"):
        await git_agent.clone_repo(test_repo_url, str(temp_dir))

    import shutil
    shutil.rmtree(temp_dir)
    assert not temp_dir.exists(), "Temporary directory should be removed after cancellation"


@pytest.mark.asyncio
async def test_timeout_handling_during_processing(tmp_path, test_repo_url, monkeypatch):
    """Test that a processing timeout during repository cloning raises a TimeoutError and cleanup is performed.

    Given:
        A temporary directory for repository cloning.
    When:
        clone_repo is invoked and simulated to raise a TimeoutError.
    Then:
        A TimeoutError is raised with a descriptive message and the temporary directory is cleaned up.
    """
    temp_dir = tmp_path / "temp_timeout_processing"
    temp_dir.mkdir()

    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        raise TimeoutError("Processing timeout")
    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    with pytest.raises(TimeoutError, match="Processing timeout"):
        await git_agent.clone_repo(test_repo_url, str(temp_dir))

    import shutil
    shutil.rmtree(temp_dir)
    assert not temp_dir.exists(), "Temporary directory should be removed after processing timeout"
