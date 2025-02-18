"""Integration tests for standard set read endpoints.

Tests cover the standard set read API endpoints functionality while mocking
MongoDB interactions."""
import pytest
from fastapi import status
from bson import ObjectId
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from tests.utils.test_data import (
    create_standard_set_test_data,
    create_standard_test_data
)
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

@pytest.fixture
def setup_list_cursor(mock_docs=None):
    """Helper fixture to setup cursor for list operations."""
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_docs or [])
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    return mock_cursor

# Test Cases - Read
async def test_get_standard_set_by_id_success(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Existing standard set with associated standards
    set_id = ObjectId()
    standard_set = create_standard_set_test_data(set_id)
    standards = [create_standard_test_data(set_id, i) for i in range(2)]
    standard_sets_collection, standards_collection = mock_collections
    standard_sets_collection.find_one = AsyncMock(return_value=standard_set)
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=standards)
    standards_collection.find = MagicMock(return_value=mock_cursor)
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service
    
    # When: GET request is made with valid ID
    response = await async_client.get(f"/api/v1/standard-sets/{str(set_id)}")
    
    # Then: Returns 200 with standard set and its standards
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Test Standard Set"
    assert data["repository_url"] == "https://github.com/test/repo"
    assert data["custom_prompt"] == "Test prompt"
    assert data["_id"] == str(set_id)
    assert len(data["standards"]) == 2
    for i, standard in enumerate(data["standards"]):
        assert standard["text"] == f"Standard {i}"
        assert standard["repository_path"] == f"/path/to/standard_{i}"
        assert len(standard["classification_ids"]) == 2
        assert all(isinstance(id, str) for id in standard["classification_ids"])

async def test_get_standard_set_by_id_not_found(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Non-existent standard set ID
    set_id = str(ObjectId())
    standard_sets_collection, standards_collection = mock_collections
    standard_sets_collection.find_one = AsyncMock(return_value=None)
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service
    
    # When: GET request is made with non-existent ID
    response = await async_client.get(f"/api/v1/standard-sets/{set_id}")
    
    # Then: Returns 404 with not found message
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Standard set not found" in response.json()["detail"]

async def test_get_standard_set_by_id_invalid_id(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Invalid ObjectId format
    invalid_id = "invalid-id"
    standard_sets_collection, standards_collection = mock_collections
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service
    
    # When: GET request is made with invalid ID
    response = await async_client.get(f"/api/v1/standard-sets/{invalid_id}")
    
    # Then: Returns 400 with invalid format message
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid ObjectId format" in response.json()["detail"]

async def test_get_standard_set_by_id_server_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Database operation fails
    set_id = str(ObjectId())
    standard_sets_collection, standards_collection = mock_collections
    standard_sets_collection.find_one = AsyncMock(
        side_effect=Exception("Database error")
    )
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service
    
    # When: GET request is made
    response = await async_client.get(f"/api/v1/standard-sets/{set_id}")
    
    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Internal server error" in response.json()["detail"]

async def test_get_all_standard_sets_success(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Existing standard sets in database
    standard_sets = [
        create_standard_set_test_data(ObjectId()) for _ in range(2)
    ]
    standard_sets_collection, _ = mock_collections
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=standard_sets)
    standard_sets_collection.find = MagicMock(return_value=mock_cursor)
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: GET request is made for all standard sets
    response = await async_client.get("/api/v1/standard-sets")

    # Then: Returns 200 with list of standard sets
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    for standard_set in data:
        assert "_id" in standard_set
        assert isinstance(standard_set["_id"], str)
        assert "name" in standard_set
        assert "repository_url" in standard_set
        assert "custom_prompt" in standard_set
        assert "created_at" in standard_set
        assert "updated_at" in standard_set

async def test_get_all_standard_sets_empty(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: No standard sets in database
    standard_sets_collection, _ = mock_collections
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    standard_sets_collection.find = MagicMock(return_value=mock_cursor)
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: GET request is made for all standard sets
    response = await async_client.get("/api/v1/standard-sets")

    # Then: Returns 200 with empty list
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 0
    assert isinstance(data, list)

async def test_get_all_standard_sets_database_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Database operation fails
    standard_sets_collection, _ = mock_collections
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(side_effect=Exception("Database error"))
    standard_sets_collection.find = MagicMock(return_value=mock_cursor)
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: GET request is made
    response = await async_client.get("/api/v1/standard-sets")

    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Error getting all standard sets: Database error" in response.json()["detail"]

async def test_get_all_standard_sets_repository_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Repository error in get_all_standard_sets
    standard_sets_collection, _ = mock_collections
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(side_effect=Exception("Repository error"))
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    standard_sets_collection.find = MagicMock(return_value=mock_cursor)
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: GET request is made
    response = await async_client.get("/api/v1/standard-sets")

    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Repository error" in response.json()["detail"]

async def test_get_standard_sets_unexpected_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Repository operation fails with unexpected error
    standard_sets_collection, _ = mock_collections
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(side_effect=Exception("Unexpected error"))
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    standard_sets_collection.find = MagicMock(return_value=mock_cursor)
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: GET request is made
    response = await async_client.get("/api/v1/standard-sets")

    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "Error getting all standard sets: Unexpected error"

async def test_get_by_id_ensure_object_id_returns_none(
    async_client,
    mock_database_setup,
    mock_collections
):
    # Given: Invalid ObjectId format
    set_id = "invalid-id"
    standard_sets_collection, _ = mock_collections
    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)
    app.dependency_overrides[get_standard_set_service] = lambda: service

    # When: GET request is made
    response = await async_client.get(f"/api/v1/standard-sets/{set_id}")

    # Then: Returns 400 with error message
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid ObjectId format" in response.json()["detail"] 