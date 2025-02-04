"""Test fixtures for the FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Any, Dict, List, Optional, Union
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
    """Helper to setup common MongoDB operation mocks.
    
    Provides a consistent way to mock MongoDB operations across tests.
    Supports both return values and side effects for all common operations.
    
    Args:
        mock_database_setup: The base database mock fixture
        
    Returns:
        A function to setup specific MongoDB operation mocks
    """
    def setup_mocks(
        collection: str,
        operation: str,
        **kwargs: Dict[str, Any]
    ) -> None:
        """Setup mocks for a specific collection and operation.
        
        Args:
            collection: Name of the MongoDB collection
            operation: Name of the operation to mock (find_one, insert_one, etc.)
            **kwargs: Additional arguments for the mock
                - return_value: The value to return
                - side_effect: Exception or function to raise/call
                - deleted_count: Number of deleted documents
                - modified_count: Number of modified documents
                - matched_count: Number of matched documents
                - inserted_id: ObjectId of inserted document
        """
        collection_mock = getattr(mock_database_setup, collection)
        operation_mock = getattr(collection_mock, operation, None)
        
        if operation_mock is None:
            raise ValueError(f"Unsupported operation: {operation}")
            
        # Reset any previous mocks
        if hasattr(operation_mock, 'reset_mock'):
            operation_mock.reset_mock()
        
        # Handle side_effect if provided
        if "side_effect" in kwargs:
            operation_mock.side_effect = kwargs["side_effect"]
            return

        # Handle return values based on operation type
        if operation == "find_one":
            operation_mock.return_value = kwargs.get("return_value")
        elif operation == "find":
            mock_find = MagicMock()
            mock_find.to_list = AsyncMock(return_value=kwargs.get("return_value", []))
            collection_mock.find = MagicMock(return_value=mock_find)
        elif operation == "find_one_and_replace":
            operation_mock.return_value = kwargs.get("return_value")
        elif operation == "find_one_and_update":
            operation_mock.return_value = kwargs.get("return_value")
        elif operation == "insert_one":
            mock_result = MagicMock()
            mock_result.inserted_id = kwargs.get("inserted_id", ObjectId())
            operation_mock.return_value = mock_result
        elif operation == "delete_one":
            mock_result = MagicMock()
            mock_result.deleted_count = kwargs.get("deleted_count", 1)
            operation_mock.return_value = mock_result
        elif operation == "delete_many":
            mock_result = MagicMock()
            mock_result.deleted_count = kwargs.get("deleted_count", 1)
            operation_mock.return_value = mock_result
        elif operation == "update_one":
            mock_result = MagicMock()
            mock_result.modified_count = kwargs.get("modified_count", 1)
            mock_result.matched_count = kwargs.get("matched_count", 1)
            operation_mock.return_value = mock_result
        elif operation == "replace_one":
            mock_result = MagicMock()
            mock_result.modified_count = kwargs.get("modified_count", 1)
            operation_mock.return_value = mock_result
        elif operation == "count_documents":
            operation_mock.return_value = kwargs.get("return_value", 0)
            
    return setup_mocks 