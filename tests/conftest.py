"""Test fixtures for the FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from src.main import app
from datetime import datetime, UTC
from bson import ObjectId

@pytest.fixture(autouse=True)
async def mock_database_setup():
    """Mock all database-related components."""
    # Create mock database with async methods
    mock_db = AsyncMock()
    mock_db.client = MagicMock()
    
    # Mock the database initialization
    with patch("src.main.init_database", return_value=mock_db), \
         patch("src.database.database_utils.client", new=MagicMock()), \
         patch("src.database.database_utils.get_database", return_value=mock_db), \
         patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=MagicMock()):
        
        # Set the mock db in app state
        app.state.db = mock_db
        yield mock_db

@pytest.fixture(autouse=True)
async def reset_app_state():
    """Reset application state before each test."""
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client(mock_database_setup):
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
async def async_client(mock_database_setup):
    """Create an async test client for the FastAPI application.
    
    Uses ASGITransport to make requests directly to the FastAPI app
    without making real HTTP calls.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables."""
    monkeypatch.setenv("MONGODB_URL", "mongodb://test:27017")
    monkeypatch.setenv("DATABASE_NAME", "test_db")

@pytest.fixture
def mock_mongodb_response():
    """Helper to create MongoDB-schema compliant responses."""
    def _create_doc(name: str = "Test Classification") -> dict:
        """Create a MongoDB document with correct schema."""
        return {
            "_id": ObjectId(),
            "name": name,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
    return _create_doc

@pytest.fixture
def mock_mongodb_operations(mock_database_setup):
    """Helper to setup common MongoDB operation mocks."""
    def setup_mocks(collection: str, operation: str, **kwargs):
        """Setup mocks for a specific collection and operation."""
        collection_mock = getattr(mock_database_setup, collection)
        
        if operation == "find_one":
            collection_mock.find_one.return_value = kwargs.get("return_value")
        elif operation == "insert_one":
            collection_mock.insert_one.return_value.inserted_id = kwargs.get("inserted_id", ObjectId())
        elif operation == "delete_one":
            collection_mock.delete_one.return_value.deleted_count = kwargs.get("deleted_count", 1)
        elif operation == "update_one":
            collection_mock.update_one.return_value.modified_count = kwargs.get("modified_count", 1)
            collection_mock.update_one.return_value.matched_count = kwargs.get("matched_count", 1)
            
    return setup_mocks 