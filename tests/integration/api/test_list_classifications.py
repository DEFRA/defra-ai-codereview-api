"""Integration tests for classification listing endpoints.

Tests cover the classification listing API endpoints functionality while mocking
MongoDB interactions."""
import pytest
from fastapi import status
from bson import ObjectId
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from tests.utils.test_data import (
    valid_classification_data,
    create_classification_test_data
)
from src.api.dependencies import get_classification_service
from src.services.classification_service import ClassificationService
from src.repositories.classification_repo import ClassificationRepository
from src.main import app

# Test Setup and Fixtures
@pytest.fixture(autouse=True)
async def setup_and_teardown():
    """Setup and teardown for each test."""
    # Setup
    yield
    # Teardown
    app.dependency_overrides = {}

@pytest.fixture
async def mock_collections():
    """Setup mock collections for tests."""
    classifications_collection = AsyncMock()
    
    # Mock the database property
    mock_db = AsyncMock()
    type(classifications_collection).database = PropertyMock(return_value=mock_db)
    
    return classifications_collection

@pytest.fixture
def setup_service(mock_database_setup, mock_collections):
    """Helper fixture to setup service with mocked dependencies."""
    classifications_collection = mock_collections
    mock_database_setup.classifications = classifications_collection
    
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    return service, classifications_collection

@pytest.fixture
def setup_list_cursor(mock_docs=None):
    """Helper fixture to setup cursor for list operations."""
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_docs or [])
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    return mock_cursor

# Test Cases - List
async def test_list_classifications_success(
    async_client,
    mock_database_setup,
    mock_collections,
    valid_classification_data
):
    # Given: Existing classifications in the database
    classifications_collection = mock_collections
    mock_doc = create_classification_test_data(valid_classification_data["name"])
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[mock_doc])
    classifications_collection.find = MagicMock(return_value=mock_cursor)
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: GET request is made
    response = await async_client.get("/api/v1/classifications")
    
    # Then: Returns 200 with list of classifications
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == valid_classification_data["name"]
    assert "_id" in data[0]
    assert "created_at" in data[0]
    assert "updated_at" in data[0]

async def test_list_classifications_failure(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Database operation fails
    classifications_collection = mock_collections
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(side_effect=Exception("Database error"))
    classifications_collection.find = MagicMock(return_value=mock_cursor)
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: GET request is made
    response = await async_client.get("/api/v1/classifications")
    
    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to retrieve classifications" in response.json()["detail"]

async def test_list_classifications_empty(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test listing classifications when none exist."""
    # Given: Empty database
    classifications_collection = mock_collections
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    classifications_collection.find = MagicMock(return_value=mock_cursor)
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: GET request is made
    response = await async_client.get("/api/v1/classifications")
    
    # Then: Returns 200 with empty list
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0 