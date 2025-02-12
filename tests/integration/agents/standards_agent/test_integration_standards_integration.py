import shutil
import pytest
from pathlib import Path
import git

# Import the function to test from standards_agent
from src.agents.standards_agent import process_standard_set


@pytest.mark.asyncio
async def test_standards_integration_updates(tmp_path, monkeypatch):
    """Test that the standards processing updates the database as expected."""
    # Create a fake repository
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    (fake_repo / "standard.md").write_text("# Standard Content")

    # Fake clone_repo to return fake_repo
    async def fake_clone_repo(url: str, dest: str):
        return fake_repo
    monkeypatch.setattr(
        "src.agents.git_repos_agent.clone_repo", fake_clone_repo)
    monkeypatch.setattr(
        "src.agents.standards_agent.clone_repo", fake_clone_repo)
    monkeypatch.setattr(git.Repo, "clone_from",
                        lambda *args, **kwargs: fake_repo)

    # Create a fake database with a flag
    class FakeDB:
        def __init__(self):
            self.processed = False

        async def list_collection_names(self):
            return []
    fake_db_instance = FakeDB()

    async def fake_get_database():
        return fake_db_instance
    monkeypatch.setattr(
        "src.agents.standards_agent.get_database", fake_get_database)

    # Fake get_classifications returns dummy classifications
    async def fake_get_classifications(db):
        return ["class1", "class2"]
    monkeypatch.setattr(
        "src.agents.standards_agent.get_classifications", fake_get_classifications)

    # Patch process_standards to update the fake db flag and capture parameters
    captured = {}

    async def fake_process_standards(db, repo, standard_set_id, classifications):
        db.processed = True
        captured['repo'] = repo
        captured['standard_set_id'] = standard_set_id
        captured['classifications'] = classifications
    monkeypatch.setattr(
        "src.agents.standards_agent.process_standards", fake_process_standards)

    # Patch cleanup_repository to do nothing
    def fake_cleanup_repository(repo):
        return
    monkeypatch.setattr(
        "src.agents.standards_agent.cleanup_repository", fake_cleanup_repository)

    # Call process_standard_set
    standard_set_id = "std-set-1"
    repository_url = "http://fake.repo/integration"
    result = await process_standard_set(standard_set_id, repository_url)

    # process_standard_set does not return a value on success
    assert result is None, "Expected process_standard_set to return None on success"
    # Verify the fake DB was updated
    assert fake_db_instance.processed is True, "Database should be marked as processed"
    # Verify captured parameters
    assert captured.get(
        'standard_set_id') == standard_set_id, "Standard set ID should be passed correctly"
    assert captured.get('classifications') == [
        "class1", "class2"], "Classifications should match dummy data"


@pytest.mark.asyncio
async def test_classification_flow(tmp_path, monkeypatch):
    """Test that the classifications flow through processing correctly."""
    # Create a fake repository
    fake_repo = tmp_path / "fake_repo_class_flow"
    fake_repo.mkdir()
    (fake_repo / "standard.md").write_text("# Standard Content for classification flow")

    async def fake_clone_repo(url: str, dest: str):
        return fake_repo
    monkeypatch.setattr(
        "src.agents.git_repos_agent.clone_repo", fake_clone_repo)
    monkeypatch.setattr(
        "src.agents.standards_agent.clone_repo", fake_clone_repo)
    monkeypatch.setattr(git.Repo, "clone_from",
                        lambda *args, **kwargs: fake_repo)

    # Fake get_database
    async def fake_get_database():
        class DummyDB:
            async def list_collection_names(self):
                return []
        return DummyDB()
    monkeypatch.setattr(
        "src.agents.standards_agent.get_database", fake_get_database)

    # Fake get_classifications returns a specific list
    dummy_classifications = ["A", "B", "C"]

    async def fake_get_classifications(db):
        return dummy_classifications
    monkeypatch.setattr(
        "src.agents.standards_agent.get_classifications", fake_get_classifications)

    # Capture the classifications passed to process_standards
    captured_classifications = None

    async def fake_process_standards(db, repo, standard_set_id, classifications):
        nonlocal captured_classifications
        captured_classifications = classifications
    monkeypatch.setattr(
        "src.agents.standards_agent.process_standards", fake_process_standards)

    def fake_cleanup_repository(repo):
        return
    monkeypatch.setattr(
        "src.agents.standards_agent.cleanup_repository", fake_cleanup_repository)

    # Call process_standard_set
    standard_set_id = "std-set-classflow"
    repository_url = "http://fake.repo/classflow"
    result = await process_standard_set(standard_set_id, repository_url)

    assert result is None, "Expected process_standard_set to return None"
    # Verify that the classifications passed are as expected
    assert captured_classifications == dummy_classifications, "Classification flow should pass correct dummy classifications"
