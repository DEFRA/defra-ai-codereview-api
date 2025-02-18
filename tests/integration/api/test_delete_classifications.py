"""Integration tests for classification deletion endpoints.

Tests cover the classification deletion API endpoints functionality while mocking
MongoDB interactions."""
import pytest
from fastapi import status
from bson import ObjectId
from unittest.mock import AsyncMock, MagicMock, PropertyMock
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

# Test Cases - Delete
async def test_delete_classification_success(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Valid classification ID
    classification_id = str(ObjectId())
    classifications_collection = mock_collections
    mock_result = AsyncMock()
    mock_result.deleted_count = 1
    classifications_collection.delete_one = AsyncMock(return_value=mock_result)
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/classifications/{classification_id}")
    
    # Then: Returns 200 with success message
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"

async def test_delete_classification_not_found(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Non-existent classification ID
    classification_id = str(ObjectId())
    classifications_collection = mock_collections
    mock_result = AsyncMock()
    mock_result.deleted_count = 0
    classifications_collection.delete_one = AsyncMock(return_value=mock_result)
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/classifications/{classification_id}")
    
    # Then: Returns 404 with not found message
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Classification not found" in response.json()["detail"]

async def test_delete_classification_invalid_id(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Invalid ObjectId format
    invalid_id = "invalid-id"
    classifications_collection = mock_collections
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/classifications/{invalid_id}")
    
    # Then: Returns 400 with error message
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error_detail = response.json()["detail"]
    assert "Invalid ObjectId format" in error_detail
    assert isinstance(error_detail, str)  # Ensure consistent error format

async def test_delete_classification_server_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Database operation throws unexpected error
    valid_id = str(ObjectId())
    classifications_collection = mock_collections
    classifications_collection.delete_one = AsyncMock(
        side_effect=Exception("Unexpected database error")
    )
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/classifications/{valid_id}")
    
    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to delete classification" in response.json()["detail"]

async def test_delete_classification_db_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test delete classification with database error before delete."""
    # Given: Valid ID but database find_one fails
    classification_id = str(ObjectId())
    classifications_collection = mock_collections
    classifications_collection.find_one = AsyncMock(side_effect=Exception("Database error"))
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/classifications/{classification_id}")
    
    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to delete classification" in response.json()["detail"]

async def test_delete_classification_empty_id(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test delete classification with empty ID."""
    # Given: Empty classification ID
    classifications_collection = mock_collections
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: DELETE request is made with empty ID
    response = await async_client.delete("/api/v1/classifications/ ")  # Space in path parameter
    
    # Then: Returns 400 bad request (invalid ObjectId)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid ObjectId format" in response.json()["detail"] 