"""Integration tests for standard set deletion endpoints.

Tests cover the standard set deletion API endpoints functionality while mocking
MongoDB interactions."""
import pytest
from fastapi import status
from bson import ObjectId
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from tests.utils.test_data import create_standard_set_test_data
from src.api.dependencies import get_standard_set_service
from src.services.standard_set_service import StandardSetService
from src.repositories.standard_set_repo import StandardSetRepository
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
    standard_sets_collection = AsyncMock()
    standards_collection = AsyncMock()
    
    # Mock the database property to return a mock that has get_collection
    mock_db = AsyncMock()
    mock_db.get_collection = MagicMock(return_value=standards_collection)
    type(standard_sets_collection).database = PropertyMock(return_value=mock_db)
    
    return standard_sets_collection, standards_collection

@pytest.fixture
def setup_service(mock_database_setup, mock_collections):
    """Helper fixture to setup service with mocked dependencies."""
    standard_sets_collection, standards_collection = mock_collections
    mock_database_setup.standard_sets = standard_sets_collection
    mock_database_setup.standards = standards_collection
    
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service
    
    return service, standard_sets_collection, standards_collection

# Test Cases - Delete
async def test_delete_standard_set_success(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Existing standard set
    set_id = ObjectId()
    standard_sets_collection, standards_collection = mock_collections
    standards_collection.delete_many = AsyncMock()
    mock_result = AsyncMock()
    mock_result.deleted_count = 1
    standard_sets_collection.delete_one = AsyncMock(return_value=mock_result)
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: DELETE request is made with valid ID
    response = await async_client.delete(f"/api/v1/standard-sets/{str(set_id)}")

    # Then: Returns 200 success response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"

async def test_delete_standard_set_not_found(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Non-existent standard set ID
    set_id = str(ObjectId())
    standard_sets_collection, standards_collection = mock_collections
    standards_collection.delete_many = AsyncMock()
    mock_result = AsyncMock()
    mock_result.deleted_count = 0
    standard_sets_collection.delete_one = AsyncMock(return_value=mock_result)
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: DELETE request is made with non-existent ID
    response = await async_client.delete(f"/api/v1/standard-sets/{set_id}")

    # Then: Returns 404 not found
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Standard set not found" in response.json()["detail"]

async def test_delete_standard_set_database_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Database operation fails
    set_id = str(ObjectId())
    standard_sets_collection, standards_collection = mock_collections
    standard_sets_collection.delete_one = AsyncMock(
        side_effect=Exception("Database error")
    )
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/standard-sets/{set_id}")

    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to delete standard set: Database error" in response.json()["detail"]

async def test_delete_standard_set_standards_deletion_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Error during standards deletion
    set_id = str(ObjectId())
    standard_sets_collection, standards_collection = mock_collections
    standard_sets_collection.find_one = AsyncMock(return_value={"_id": ObjectId(set_id)})
    standards_collection.delete_many = AsyncMock(side_effect=Exception("Standards deletion error"))
    mock_result = AsyncMock()
    mock_result.deleted_count = 1
    standard_sets_collection.delete_one = AsyncMock(return_value=mock_result)
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/standard-sets/{set_id}")

    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to delete standard set: Standards deletion error" in response.json()["detail"]

async def test_delete_standard_set_invalid_object_id(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Invalid ObjectId format
    invalid_id = "invalid-id"
    standard_sets_collection, _ = mock_collections
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: DELETE request is made with invalid ID
    response = await async_client.delete(f"/api/v1/standard-sets/{invalid_id}")

    # Then: Returns 400 with invalid format message
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f"Invalid ObjectId format: {invalid_id}" in response.json()["detail"]

async def test_delete_standard_set_repository_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Repository error during deletion
    set_id = str(ObjectId())
    standard_sets_collection, standards_collection = mock_collections
    standard_sets_collection.find_one = AsyncMock(return_value={"_id": ObjectId(set_id)})
    standards_collection.delete_many = AsyncMock()
    standard_sets_collection.delete_one = AsyncMock(side_effect=Exception("Repository error"))
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/standard-sets/{set_id}")

    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Repository error" in response.json()["detail"]

async def test_delete_standard_set_unexpected_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Service throws unexpected error
    set_id = str(ObjectId())
    standard_sets_collection, _ = mock_collections
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    # Mock service to raise generic exception
    service.delete_standard_set = AsyncMock(side_effect=Exception("Unexpected error"))
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/standard-sets/{set_id}")

    # Then: Returns 500 with internal server error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Internal server error" in response.json()["detail"]

async def test_delete_ensure_object_id_returns_none(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Invalid ObjectId format
    invalid_id = "invalid-id"
    standard_sets_collection, _ = mock_collections
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/standard-sets/{invalid_id}")

    # Then: Returns 400 with error message
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid ObjectId format" in response.json()["detail"] 