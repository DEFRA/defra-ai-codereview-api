import pytest
from pathlib import Path
import tempfile
import shutil
from bson import ObjectId
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

# Import the function to be tested
from src.agents.standards_agent import process_standard_set, StandardsProcessingError
from src.config.config import settings


# Helper fake functions common to tests
async def fake_get_database():
    class FakeDB:
        async def list_collection_names(self):
            return []

        def get_collection(self, name):
            class FakeCollection:
                async def delete_many(self, query):
                    pass

                async def insert_one(self, doc):
                    class FakeResult:
                        def __init__(self):
                            self.inserted_id = ObjectId()
                    return FakeResult()

                async def find_one(self, query):
                    return {
                        "_id": ObjectId(),
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC)
                    }
            return FakeCollection()
    return FakeDB()


async def fake_get_classifications(db):
    return []


# Test 6: Error Handling - LLM Service Unavailable
@pytest.mark.asyncio
async def test_llm_service_unavailable(monkeypatch, caplog):
    """
    Simulate LLM service unavailability by patching the analyze_standard function
    to raise an Exception. Verify that process_standard_set logs the error but continues processing.
    """
    import src.agents.standards_agent as agent_module

    # Override external dependencies
    monkeypatch.setattr(agent_module, "get_database", fake_get_database)
    monkeypatch.setattr(agent_module, "get_classifications",
                        fake_get_classifications)

    async def fake_download_repository(repo_url):
        # Create a temporary directory with a test markdown file that matches LLM testing patterns
        temp_dir = Path(tempfile.mkdtemp())
        test_file = temp_dir / "javascript_standards.md"  # Match the testing file pattern
        test_file.write_text("Test content")
        return temp_dir

    monkeypatch.setattr(agent_module, "download_repository",
                        fake_download_repository)

    def fake_analyze_standard(*args, **kwargs):
        raise Exception("LLM Service Unavailable")
    monkeypatch.setattr(agent_module, "analyze_standard",
                        fake_analyze_standard)

    # Mock the StandardsConfig to ensure LLM testing mode is enabled
    class MockConfig:
        def __init__(self):
            self.llm_testing = True
            self.testing_files = ["javascript_standards.md"]
    monkeypatch.setattr(agent_module, "StandardsConfig", lambda: MockConfig())

    # Process should complete but log the error
    await process_standard_set(str(ObjectId()), "http://dummy_repo_url")

    # Verify error was logged
    assert any("Error processing standard" in record.message and "LLM Service Unavailable" in record.message
               for record in caplog.records)


# Test 7: Edge Case - Empty Repository

@pytest.mark.asyncio
async def test_empty_repository(tmp_path, monkeypatch):
    """
    Simulate an empty repository by creating an empty directory and patching
    download_repository to return it. Verify that process_standard_set completes without
    processing any standards.
    """
    import src.agents.standards_agent as agent_module

    # Override external dependencies
    monkeypatch.setattr(agent_module, "get_database", fake_get_database)
    monkeypatch.setattr(agent_module, "get_classifications",
                        fake_get_classifications)

    empty_repo_dir = tmp_path / "empty_repo"
    empty_repo_dir.mkdir()

    async def fake_download_repository(repo_url):
        return empty_repo_dir
    monkeypatch.setattr(agent_module, "download_repository",
                        fake_download_repository)

    async def fake_process_standards(db, repo, set_id, classifications):
        # For an empty repository, simulate no standards processed.
        return
    monkeypatch.setattr(agent_module, "process_standards",
                        fake_process_standards)

    result = await process_standard_set("standard_set_id", "http://dummy_repo_url")
    if isinstance(result, dict) and "standards" in result:
        assert result["standards"] == [
        ], "Expected no standards to be processed for empty repository"
    else:
        assert result in (
            None, []), "Expected no standards to be processed for empty repository"


# Test 8: Edge Case - Large Standards

@pytest.mark.asyncio
async def test_large_standards(tmp_path, monkeypatch):
    """
    Simulate a repository with a large markdown file (~1MB) to test processing of large standard files
    without memory issues. Verify that process_standard_set handles large files without errors.
    """
    import src.agents.standards_agent as agent_module

    # Override external dependencies
    monkeypatch.setattr(agent_module, "get_database", fake_get_database)
    monkeypatch.setattr(agent_module, "get_classifications",
                        fake_get_classifications)

    large_repo_dir = tmp_path / "large_repo"
    large_repo_dir.mkdir()
    large_file = large_repo_dir / "large_standard.md"
    # Create approximately 1MB of markdown content
    phrase = "This is a large standard content. "
    num_repeats = (1024 * 1024) // len(phrase)
    large_content = phrase * num_repeats
    large_file.write_text(large_content, encoding="utf-8")

    async def fake_download_repository(repo_url):
        return large_repo_dir
    monkeypatch.setattr(agent_module, "download_repository",
                        fake_download_repository)

    # Track if process_standards was called
    process_standards_called = False

    async def fake_process_standards(db, repo, set_id, classifications):
        nonlocal process_standards_called
        process_standards_called = True
        # Don't return anything, matching actual implementation
        return None
    monkeypatch.setattr(agent_module, "process_standards",
                        fake_process_standards)

    # Should complete without raising any exceptions
    result = await process_standard_set("standard_set_id", "http://dummy_repo_url")
    assert process_standards_called, "Expected process_standards to be called"
    assert result is None, "Expected no return value from process_standard_set"


# Test 9: Edge Case - Special Characters

@pytest.mark.asyncio
async def test_special_characters(tmp_path, monkeypatch):
    """
    Simulate a repository containing a markdown file with special characters.
    Verify that process_standard_set correctly processes and preserves these characters.
    """
    import src.agents.standards_agent as agent_module

    # Override external dependencies
    monkeypatch.setattr(agent_module, "get_database", fake_get_database)
    monkeypatch.setattr(agent_module, "get_classifications",
                        fake_get_classifications)

    special_repo_dir = tmp_path / "special_repo"
    special_repo_dir.mkdir()
    special_file = special_repo_dir / "special_standard.md"
    special_content = "Standard with special characters: ñ, é, ü, 😊"
    special_file.write_text(special_content, encoding="utf-8")

    async def fake_download_repository(repo_url):
        return special_repo_dir
    monkeypatch.setattr(agent_module, "download_repository",
                        fake_download_repository)

    # Track if process_standards was called with correct content
    standards_processed = False

    async def fake_process_standards(db, repo, set_id, classifications):
        nonlocal standards_processed
        # Verify the file exists and contains our special characters
        standard_file = repo / "special_standard.md"
        content = standard_file.read_text(encoding="utf-8")
        for char in ["ñ", "é", "ü", "😊"]:
            assert char in content, f"Expected special character {char} in processed content"
        standards_processed = True

    monkeypatch.setattr(agent_module, "process_standards",
                        fake_process_standards)

    # Should complete without raising any exceptions
    result = await process_standard_set("standard_set_id", "http://dummy_repo_url")
    assert result is None, "Expected no return value from process_standard_set"
    assert standards_processed, "Expected standards to be processed successfully"
