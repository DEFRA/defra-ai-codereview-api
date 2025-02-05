"""Integration tests for classification endpoints.

Tests cover the classification API endpoints functionality while mocking
MongoDB interactions."""
import pytest
from fastapi import status
from bson import ObjectId
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from tests.utils.test_data import (
    valid_classification_data,
    create_classification_test_data
)
from src.api.dependencies import get_classification_service
from src.services.classification_service import ClassificationService
from src.repositories.classification_repo import ClassificationRepository
from src.main import app

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

# Test Cases - Create
async def test_create_classification_success(
    async_client,
    mock_database_setup,
    mock_collections,
    valid_classification_data
):
    # Given: A valid classification payload
    classifications_collection = mock_collections
    classifications_collection.find_one = AsyncMock(return_value=None)
    classifications_collection.insert_one = AsyncMock()
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: POST request is made
    response = await async_client.post(
        "/api/v1/classifications",
        json=valid_classification_data
    )
    
    # Then: Returns 201 with created classification
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == valid_classification_data["name"]
    assert "_id" in data

async def test_create_classification_failure(
    async_client,
    mock_database_setup,
    mock_collections,
    valid_classification_data
):
    # Given: Database operation fails
    classifications_collection = mock_collections
    classifications_collection.find_one = AsyncMock(return_value=None)
    classifications_collection.insert_one = AsyncMock(
        side_effect=Exception("Database error")
    )
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: POST request is made
    response = await async_client.post(
        "/api/v1/classifications",
        json=valid_classification_data
    )
    
    # Then: Returns 400 with error message
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Database error" in response.json()["detail"]

async def test_create_classification_duplicate(
    async_client,
    mock_database_setup,
    mock_collections,
    valid_classification_data
):
    # Given: Classification already exists
    classifications_collection = mock_collections
    existing_doc = create_classification_test_data(valid_classification_data["name"])
    classifications_collection.find_one = AsyncMock(return_value=existing_doc)
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: POST request is made with same name
    response = await async_client.post(
        "/api/v1/classifications",
        json=valid_classification_data
    )
    
    # Then: Returns 201 with existing classification
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == valid_classification_data["name"]
    assert data["_id"] == str(existing_doc["_id"])
    # Verify timestamps are preserved from existing doc by comparing parsed datetimes
    assert datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) == existing_doc["created_at"]
    assert datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')) == existing_doc["updated_at"]

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