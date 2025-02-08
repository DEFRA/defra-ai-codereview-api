"""Integration tests for classification creation endpoints.

Tests cover the classification creation API endpoints functionality while mocking
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
def setup_mock_result(operation_type="insert", count=1, doc_id=None):
    """Helper fixture to setup mock results for database operations.
    
    Args:
        operation_type (str): Type of operation ('insert', 'update', 'delete')
        count (int): Number of affected documents for update/delete operations
        doc_id (ObjectId, optional): Document ID for insert operations
    """
    class MockResult:
        def __init__(self):
            if operation_type == "insert":
                self.inserted_id = doc_id or ObjectId()
            elif operation_type == "update":
                self.modified_count = count
                self.matched_count = count
            elif operation_type == "delete":
                self.deleted_count = count
    
    return MockResult()

@pytest.fixture
def setup_error_mock(error_message="Database error"):
    """Helper fixture to setup error mocks for database operations.
    
    Args:
        error_message (str): Custom error message for the exception
    """
    return AsyncMock(side_effect=Exception(error_message))

# Test Cases - Create
async def test_create_classification_success(
    async_client,
    setup_service,
    setup_mock_result,
    valid_classification_data
):
    """Test successful creation of a classification."""
    # Given: A valid classification payload
    _, classifications_collection = setup_service
    classifications_collection.find_one = AsyncMock(return_value=None)
    classifications_collection.insert_one = AsyncMock(return_value=setup_mock_result)
    
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
    setup_service,
    setup_error_mock,
    valid_classification_data
):
    """Test classification creation with database error."""
    # Given: Database operation fails
    _, classifications_collection = setup_service
    classifications_collection.find_one = AsyncMock(return_value=None)
    classifications_collection.insert_one = setup_error_mock
    
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

async def test_create_classification_invalid_input(
    async_client,
    setup_service
):
    """Test classification creation with invalid input."""
    # Given: Invalid classification data
    invalid_data = {"invalid_field": "test"}
    
    # When: POST request is made with invalid data
    response = await async_client.post(
        "/api/v1/classifications",
        json=invalid_data
    )
    
    # Then: Returns 422 validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

async def test_create_classification_empty_name(
    async_client,
    setup_service
):
    """Test classification creation with empty name."""
    # Given: Classification data with empty name
    invalid_data = {"name": ""}
    
    # When: POST request is made with empty name
    response = await async_client.post(
        "/api/v1/classifications",
        json=invalid_data
    )
    
    # Then: Returns 422 validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

async def test_get_classification_by_name_not_found(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test get classification by name when it doesn't exist."""
    # Given: Non-existent classification name
    classifications_collection = mock_collections
    classifications_collection.find_one = AsyncMock(return_value=None)
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: POST request is made with non-existent name
    response = await async_client.post(
        "/api/v1/classifications",
        json={"name": "non-existent"}
    )
    
    # Then: Returns 201 with new classification
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "non-existent"

async def test_get_classification_by_name_db_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test get classification by name when database errors."""
    # Given: Database error when checking name
    classifications_collection = mock_collections
    classifications_collection.find_one = AsyncMock(side_effect=Exception("Database error"))
    repo = ClassificationRepository(classifications_collection)
    service = ClassificationService(mock_database_setup, repo)
    app.dependency_overrides[get_classification_service] = lambda: service
    
    # When: POST request is made
    response = await async_client.post(
        "/api/v1/classifications",
        json={"name": "test"}
    )
    
    # Then: Returns 400 with error message
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Database error" in response.json()["detail"] 