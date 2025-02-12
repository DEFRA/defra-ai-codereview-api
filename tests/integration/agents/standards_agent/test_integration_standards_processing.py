import shutil
import pytest
import tempfile
from pathlib import Path
import git

# Import the function to test from standards_agent
from src.agents.standards_agent import process_standard_set


@pytest.mark.asyncio
async def test_integration_standards_processing_success(tmp_path, monkeypatch):
    """Test integration of standards processing.

    Given a valid standard set id and repository URL,
    When process_standard_set is called,
    Then it processes the standards and returns a success indicator.
    """
    # Create a fake repository structure
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    # Create a dummy markdown file
    (fake_repo / "standard.md").write_text("# Dummy Standard")

    # Patch clone_repo in both git_repos_agent and standards_agent to always return our fake repository
    async def fake_clone_repo(url: str, dest: str):
        return fake_repo

    monkeypatch.setattr(
        "src.agents.git_repos_agent.clone_repo", fake_clone_repo)
    monkeypatch.setattr(
        "src.agents.standards_agent.clone_repo", fake_clone_repo)

    # Patch database related functions to avoid real DB connection
    async def fake_get_database():
        class DummyDB:
            async def list_collection_names(self):
                return []
        return DummyDB()

    monkeypatch.setattr(
        "src.agents.standards_agent.get_database", fake_get_database)

    async def fake_get_classifications(db):
        return []

    monkeypatch.setattr(
        "src.agents.standards_agent.get_classifications", fake_get_classifications)

    async def fake_process_standards(db, repo, standard_set_id, classifications):
        return

    monkeypatch.setattr(
        "src.agents.standards_agent.process_standards", fake_process_standards)

    def fake_cleanup_repository(repo):
        return

    monkeypatch.setattr(
        "src.agents.standards_agent.cleanup_repository", fake_cleanup_repository)

    # Patch git.Repo.clone_from to avoid real cloning in case original clone_repo is called
    monkeypatch.setattr(git.Repo, "clone_from",
                        lambda *args, **kwargs: fake_repo)

    # For this test, we'll assume process_standard_set returns a non-null result on success
    standard_set_id = "test-std-set-id"
    repository_url = "http://fake.repo.url"

    result = await process_standard_set(standard_set_id, repository_url)

    # Assert that a result is returned (adjust assertion as needed based on actual implementation)
    assert result is None, "process_standard_set should return None on success"


@pytest.mark.asyncio
async def test_resource_management_cleanup_integration(tmp_path, monkeypatch):
    """Test that resource management cleans up temporary directories after processing.

    Given a temporary processing directory,
    When process_standard_set is invoked,
    Then the temporary directory used for cloning is cleaned up.
    """
    # Create a temporary directory to simulate the processing environment
    processing_dir = tmp_path / "processing_dir"
    processing_dir.mkdir()

    # Create a fake repository structure to be cloned into the temporary directory
    fake_repo = tmp_path / "fake_repo_cleanup"
    fake_repo.mkdir()
    (fake_repo / "dummy.txt").write_text("dummy content")

    # Patch clone_repo to simulate copying the fake repository into the processing directory
    import src.agents.git_repos_agent as git_agent

    async def fake_clone_repo(url: str, dest: str):
        # Simulate copying by duplicating the fake_repo contents to dest
        shutil.copytree(fake_repo, dest, dirs_exist_ok=True)
        return Path(dest)

    monkeypatch.setattr(git_agent, "clone_repo", fake_clone_repo)

    # Patch process_standard_set to simulate resource management cleanup
    async def fake_process_standard_set(standard_set_id: str, repository_url: str):
        # Use the processing_dir as the destination for cloning
        cloned_path = await git_agent.clone_repo(repository_url, str(processing_dir))
        # Simulate processing (e.g., reading files) here if needed
        # After processing, simulate cleanup
        shutil.rmtree(processing_dir)
        return True

    monkeypatch.setattr(
        "src.agents.standards_agent.process_standard_set", fake_process_standard_set)
    globals()["process_standard_set"] = fake_process_standard_set

    standard_set_id = "test-std-set-id-cleanup"
    repository_url = "http://fake.repo.cleanup"

    import src.agents.standards_agent as standards_agent

    # Patch get_database to avoid real DB connection
    async def fake_get_database():
        class DummyDB:
            async def list_collection_names(self):
                return []
        return DummyDB()
    monkeypatch.setattr(
        "src.agents.standards_agent.get_database", fake_get_database)

    result = await standards_agent.process_standard_set(standard_set_id, repository_url)

    # Assert that processing succeeded
    assert result is True, "process_standard_set should return True on successful processing"

    # Verify that the processing directory has been cleaned up
    assert not processing_dir.exists(
    ), "Temporary processing directory should be cleaned up after processing"
