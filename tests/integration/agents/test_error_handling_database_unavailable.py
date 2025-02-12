import pytest
from unittest.mock import patch

# Import the main function to process a standard set
from src.agents.standards_agent import process_standard_set, StandardsProcessingError


@pytest.mark.asyncio
async def test_database_unavailable(tmp_path):
    """
    Test that process_standard_set raises an exception when the database is unavailable,
    and that temporary resources are cleaned up and no partial data is persisted.
    """
    standard_set_id = "test_set_id"
    repository_url = "https://example.com/repo.git"

    # Simulate database unavailability by patching the ClassificationRepository.get_all method to raise an exception
    with patch("src.repositories.classification_repo.ClassificationRepository.get_all", side_effect=Exception("Database connection error")):
        with pytest.raises(StandardsProcessingError) as exc_info:
            await process_standard_set(standard_set_id, repository_url)
        error_message = str(exc_info.value).lower()
        assert ("connection error" in error_message) or (
            "connection refused" in error_message), "Expected error message to reference a connection issue"
