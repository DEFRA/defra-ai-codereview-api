from src.agents.standards_agent import process_standard_set, StandardsProcessingError
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# Create a mock database that won't try to connect


class MockDB:
    def __init__(self):
        self.collections = {}

    def get_collection(self, name):
        if name not in self.collections:
            self.collections[name] = SimpleNamespace(insert_one=AsyncMock())
        return self.collections[name]

# Mock async function to return our mock database


async def mock_get_database():
    return MockDB()

# Assuming process_standard_set is located in src/agents/standards_agent.py

# Optionally, if available, import method to inspect stored standards
# from src.repositories.standard_repository import get_all_standards


@pytest.fixture
async def mock_database():
    """Setup mock database for tests."""
    # Create mock client and database
    mock_client = AsyncMock(spec=AsyncIOMotorClient)
    mock_db = AsyncMock(spec=AsyncIOMotorDatabase)

    # Setup database properties
    mock_db.list_collection_names = AsyncMock(return_value=["standards"])
    mock_db.command = AsyncMock()
    mock_db.create_collection = AsyncMock()

    # Setup collection
    mock_collection = AsyncMock()
    mock_db.get_collection = MagicMock(return_value=mock_collection)

    # Link client to database
    mock_client.code_reviews = mock_db

    # Mock database initialization and global variables
    with patch("src.database.database_utils.client", mock_client), \
            patch("src.database.database_utils.db", mock_db), \
            patch("src.database.database_init.init_database", return_value=mock_db):
        yield mock_db


@pytest.fixture(autouse=True)
async def setup_and_teardown():
    """Setup and teardown for each test."""
    # Setup
    yield
    # Teardown - clear any overrides if needed


@pytest.mark.asyncio
async def test_invalid_repository_error_handling(mock_database, caplog):
    """Test that repository clone failures are handled correctly."""
    # Given: Setup test data
    valid_standard_set_id = "valid_standard_set_id"
    invalid_repository_url = "http://invalid-repository-url"
    expected_error = "Failed to clone repository"

    # When: Attempt to process with invalid repository
    with patch("src.agents.standards_agent.clone_repo", side_effect=Exception(expected_error)):
        with pytest.raises(StandardsProcessingError) as excinfo:
            await process_standard_set(valid_standard_set_id, invalid_repository_url)

    # Then: Verify error handling
    error_message = str(excinfo.value)
    assert expected_error in error_message, f"Expected error message to contain '{expected_error}', but got: {error_message}"

    # Verify no database operations were performed
    mock_database.get_collection.assert_not_called()

    # Optionally, verify that no standards have been stored in the database
    # standards = get_all_standards()
    # assert standards == []
