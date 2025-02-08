"""Integration tests for code review creation endpoints.

Tests cover the code review creation API endpoints functionality while mocking
MongoDB interactions."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from fastapi import status
from bson import ObjectId
from src.models.code_review import ReviewStatus
from src.main import app
from src.api.dependencies import get_code_review_service
from src.services.code_review_service import CodeReviewService
from src.repositories.code_review_repo import CodeReviewRepository
from tests.utils.test_data import (
    create_code_review_test_data,
    valid_code_review_data,
    invalid_code_review_data,
    create_standard_set_reference
)

# Test Setup and Fixtures
@pytest.fixture(autouse=True)
async def setup_and_teardown():
    """Setup and teardown for each test."""
    # Setup
    yield
    # Teardown - clear dependency overrides
    app.dependency_overrides = {}

@pytest.fixture
async def mock_collections():
    """Setup mock collections for tests."""
    code_reviews_collection = AsyncMock()
    standard_sets_collection = AsyncMock()
    
    # Mock the database property for nested collections
    mock_db = AsyncMock()
    mock_db.get_collection = MagicMock(return_value=standard_sets_collection)
    type(code_reviews_collection).database = PropertyMock(return_value=mock_db)
    
    return code_reviews_collection, standard_sets_collection

@pytest.fixture
def setup_service(mock_database_setup, mock_collections):
    """Helper fixture to setup service with mocked dependencies."""
    code_reviews_collection, standard_sets_collection = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    mock_database_setup.standard_sets = standard_sets_collection
    
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
    return service, code_reviews_collection, standard_sets_collection

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

# Test Cases - Create Code Review
async def test_create_code_review_success(
    async_client,
    setup_service,
    setup_mock_result,
    valid_code_review_data
):
    """Test successful creation of a code review."""
    # Given: Valid code review data and mocked dependencies
    _, code_reviews_collection, standard_sets_collection = setup_service
    standard_set = create_standard_set_reference(valid_code_review_data["standard_sets"][0])
    standard_sets_collection.find_one = AsyncMock(return_value=standard_set)
    
    mock_doc = create_code_review_test_data(
        repository_url=valid_code_review_data["repository_url"],
        standard_sets=[standard_set]
    )
    code_reviews_collection.insert_one = AsyncMock(return_value=setup_mock_result)
    code_reviews_collection.find_one = AsyncMock(return_value=mock_doc)
    
    # When: Create code review request is made
    with patch('src.services.code_review_service.Process'):
        response = await async_client.post("/api/v1/code-reviews", json=valid_code_review_data)
    
    # Then: Verify response and process creation
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["repository_url"] == valid_code_review_data["repository_url"]
    assert data["status"] == ReviewStatus.STARTED
    assert "_id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert isinstance(data["standard_sets"], list)
    assert len(data["standard_sets"]) == 1
    assert data["standard_sets"][0]["_id"] == valid_code_review_data["standard_sets"][0]
    assert data["standard_sets"][0]["name"] == standard_set["name"]

async def test_create_code_review_validation_error(
    async_client,
    setup_service,
    invalid_code_review_data
):
    """Test code review creation with invalid input data."""
    # Given: Invalid test data
    
    # When: Create request is made with invalid data
    with patch('src.services.code_review_service.Process'):
        response = await async_client.post("/api/v1/code-reviews", json=invalid_code_review_data)
    
    # Then: Verify validation error response
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)

async def test_create_code_review_invalid_standard_set(
    async_client,
    setup_service,
    valid_code_review_data
):
    """Test code review creation with non-existent standard set."""
    # Given: Setup with non-existent standard set
    _, _, standard_sets_collection = setup_service
    standard_sets_collection.find_one = AsyncMock(return_value=None)
    
    # When: Create request is made
    with patch('src.services.code_review_service.Process') as mock_process:
        response = await async_client.post("/api/v1/code-reviews", json=valid_code_review_data)
    
    # Then: Verify error response and no process creation
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert f"Standard set {valid_code_review_data['standard_sets'][0]} not found" in data["detail"]
    mock_process.assert_not_called()

async def test_create_code_review_db_error(
    async_client,
    setup_service,
    setup_error_mock,
    valid_code_review_data
):
    """Test code review creation with database error."""
    # Given: Setup with database error
    _, code_reviews_collection, standard_sets_collection = setup_service
    standard_set = create_standard_set_reference(valid_code_review_data["standard_sets"][0])
    standard_sets_collection.find_one = AsyncMock(return_value=standard_set)
    code_reviews_collection.insert_one = setup_error_mock
    
    # When: Create request is made
    with patch('src.services.code_review_service.Process') as mock_process:
        response = await async_client.post("/api/v1/code-reviews", json=valid_code_review_data)
    
    # Then: Verify error response and no process creation
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert "Error creating code review" in data["detail"]
    assert "Database error" in data["detail"]
    mock_process.assert_not_called()

async def test_create_code_review_multiple_standard_sets(
    async_client,
    setup_service,
    setup_mock_result,
    valid_code_review_data
):
    """Test creating a code review with multiple standard sets."""
    # Given: Valid code review data with multiple standard sets
    _, code_reviews_collection, standard_sets_collection = setup_service
    standard_set_ids = [str(ObjectId()), str(ObjectId())]
    standard_sets = [create_standard_set_reference(id) for id in standard_set_ids]
    
    # Mock standard sets lookup
    async def mock_find_one(filter_dict):
        set_id = filter_dict["_id"]
        return next((s for s in standard_sets if str(s["_id"]) == str(set_id)), None)
    
    standard_sets_collection.find_one = AsyncMock(side_effect=mock_find_one)
    
    # Prepare test data with multiple standard sets
    test_data = valid_code_review_data.copy()
    test_data["standard_sets"] = standard_set_ids
    
    mock_doc = create_code_review_test_data(
        repository_url=test_data["repository_url"],
        standard_sets=standard_sets
    )
    code_reviews_collection.insert_one = AsyncMock(return_value=setup_mock_result)
    code_reviews_collection.find_one = AsyncMock(return_value=mock_doc)
    
    # When: Create code review request is made
    with patch('src.services.code_review_service.Process'):
        response = await async_client.post("/api/v1/code-reviews", json=test_data)
    
    # Then: Verify response
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert len(data["standard_sets"]) == len(standard_set_ids)
    for i, standard_set in enumerate(data["standard_sets"]):
        assert standard_set["_id"] == standard_set_ids[i]

async def test_create_code_review_partial_standard_sets_failure(
    async_client,
    setup_service,
    valid_code_review_data
):
    """Test create code review when some standard sets don't exist."""
    # Given: Mix of valid and invalid standard set IDs
    _, _, standard_sets_collection = setup_service
    valid_set = create_standard_set_reference(str(ObjectId()))
    
    async def mock_find_one(filter_dict):
        return valid_set if str(filter_dict["_id"]) == str(valid_set["_id"]) else None
    
    standard_sets_collection.find_one = AsyncMock(side_effect=mock_find_one)
    
    # Prepare test data with mix of valid/invalid sets
    test_data = valid_code_review_data.copy()
    test_data["standard_sets"] = [str(valid_set["_id"]), str(ObjectId())]
    
    # When: Create request is made
    with patch('src.services.code_review_service.Process'):
        response = await async_client.post("/api/v1/code-reviews", json=test_data)
    
    # Then: Verify error response
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Standard set" in data["detail"]
    assert "not found" in data["detail"]

async def test_create_code_review_duplicate_standard_sets(
    async_client,
    setup_service,
    valid_code_review_data
):
    """Test create code review with duplicate standard sets."""
    # Given: Duplicate standard set IDs
    _, code_reviews_collection, standard_sets_collection = setup_service
    standard_set = create_standard_set_reference(str(ObjectId()))
    standard_sets_collection.find_one = AsyncMock(return_value=standard_set)
    
    # Mock the insert operation to raise validation error
    async def mock_insert(*args, **kwargs):
        raise ValueError("Duplicate standard sets are not allowed")
    
    code_reviews_collection.insert_one = AsyncMock(side_effect=mock_insert)
    
    # Prepare test data with duplicate sets
    test_data = valid_code_review_data.copy()
    test_data["standard_sets"] = [str(standard_set["_id"]), str(standard_set["_id"])]
    
    # When: Create request is made
    with patch('src.services.code_review_service.Process'):
        response = await async_client.post("/api/v1/code-reviews", json=test_data)
    
    # Then: Verify error response
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Duplicate standard sets" in data["detail"] 