"""Integration tests for code reviews API endpoints.

Tests cover the code review API endpoints functionality while mocking
MongoDB interactions. Tests are organized by endpoint operation (create, read)
and follow the Given-When-Then pattern."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from fastapi import status
from bson import ObjectId
from src.models.code_review import ReviewStatus, StandardSetInfo
from src.main import app
from src.api.dependencies import get_code_review_service
from src.services.code_review_service import CodeReviewService
from src.repositories.code_review_repo import CodeReviewRepository
from tests.utils.test_data import (
    create_code_review_test_data,
    create_code_review_list_test_data,
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
def setup_list_cursor(mock_reviews=None):
    """Helper fixture to setup cursor for list operations."""
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_reviews or [])
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    return mock_cursor

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

# Test Cases - Get Single Code Review
async def test_get_code_review_by_id_success(
    async_client,
    setup_service
):
    """Test successful retrieval of a specific code review."""
    # Given: Existing code review
    _, code_reviews_collection, _ = setup_service
    standard_set_id = str(ObjectId())
    standard_set = create_standard_set_reference(standard_set_id)
    mock_review = create_code_review_test_data(
        repository_url="https://github.com/test/repo",
        standard_sets=[standard_set]
    )
    code_reviews_collection.find_one = AsyncMock(return_value=mock_review)
    
    # When: Get specific review request is made
    response = await async_client.get(f"/api/v1/code-reviews/{str(mock_review['_id'])}")
    
    # Then: Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["_id"] == str(mock_review["_id"])
    assert data["repository_url"] == mock_review["repository_url"]
    assert data["status"] == mock_review["status"]
    assert isinstance(data["standard_sets"], list)
    assert len(data["standard_sets"]) == len(mock_review["standard_sets"])
    assert isinstance(data["compliance_reports"], list)
    assert "created_at" in data
    assert "updated_at" in data

async def test_get_code_review_not_found(
    async_client,
    setup_service
):
    """Test get code review with non-existent ID."""
    # Given: Non-existent code review ID
    _, code_reviews_collection, _ = setup_service
    code_reviews_collection.find_one = AsyncMock(return_value=None)
    test_id = str(ObjectId())
    
    # When: Get request is made with non-existent ID
    response = await async_client.get(f"/api/v1/code-reviews/{test_id}")
    
    # Then: Verify not found response
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert f"Code review {test_id} not found" in data["detail"]

async def test_get_code_review_invalid_id(
    async_client,
    setup_service
):
    """Test get code review with invalid ID format."""
    # Given: Invalid ObjectId format
    invalid_id = "invalid-id"
    
    # When: Get request is made with invalid ID
    response = await async_client.get(f"/api/v1/code-reviews/{invalid_id}")
    
    # Then: Verify bad request response
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Invalid ObjectId format" in data["detail"]
    assert invalid_id in data["detail"]

async def test_get_code_review_db_error(
    async_client,
    setup_service
):
    """Test get code review with database error."""
    # Given: Database operation fails
    _, code_reviews_collection, _ = setup_service
    code_reviews_collection.find_one = AsyncMock(side_effect=Exception("Database error"))
    test_id = str(ObjectId())
    
    # When: Get request is made
    response = await async_client.get(f"/api/v1/code-reviews/{test_id}")
    
    # Then: Verify error response
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert "Error fetching code review" in data["detail"]
    assert "Database error" in data["detail"]

# Test Cases - List Code Reviews
async def test_get_all_code_reviews_success(
    async_client,
    setup_service
):
    """Test successful retrieval of all code reviews."""
    # Given: Existing code reviews
    _, code_reviews_collection, _ = setup_service
    mock_reviews = [create_code_review_list_test_data() for _ in range(2)]
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_reviews)
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    code_reviews_collection.find = MagicMock(return_value=mock_cursor)
    
    # When: Get all reviews request is made
    response = await async_client.get("/api/v1/code-reviews")
    
    # Then: Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    
    for i, review in enumerate(data):
        mock_review = mock_reviews[i]
        assert review["_id"] == str(mock_review["_id"])
        assert review["repository_url"] == mock_review["repository_url"]
        assert review["status"] == mock_review["status"]
        assert isinstance(review["standard_sets"], list)
        assert len(review["standard_sets"]) == len(mock_review["standard_sets"])
        assert "created_at" in review
        assert "updated_at" in review

async def test_get_all_code_reviews_empty(
    async_client,
    setup_service,
    setup_list_cursor
):
    """Test successful retrieval of empty code reviews list."""
    # Given: No code reviews exist
    _, code_reviews_collection, _ = setup_service
    code_reviews_collection.find = MagicMock(return_value=setup_list_cursor)
    
    # When: Get all reviews request is made
    response = await async_client.get("/api/v1/code-reviews")
    
    # Then: Verify empty response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

async def test_get_all_code_reviews_db_error(
    async_client,
    setup_service
):
    """Test get all code reviews with database error."""
    # Given: Database operation fails
    _, code_reviews_collection, _ = setup_service
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(side_effect=Exception("Database error"))
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    code_reviews_collection.find = MagicMock(return_value=mock_cursor)
    
    # When: Get all reviews request is made
    response = await async_client.get("/api/v1/code-reviews")
    
    # Then: Verify error response
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert "Error fetching code reviews" in data["detail"]
    assert "Database error" in data["detail"] 