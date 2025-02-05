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
from datetime import datetime

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

# Additional Test Cases - Create Code Review
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

# Additional Test Cases - Get Code Reviews List
async def test_get_all_code_reviews_with_sorting(
    async_client,
    setup_service
):
    """Test retrieving code reviews with correct sorting."""
    # Given: Multiple code reviews with different timestamps
    _, code_reviews_collection, _ = setup_service
    
    # Create test data with different timestamps
    mock_reviews = [
        create_code_review_test_data(
            repository_url="https://github.com/test/repo1",
            standard_sets=[]
        ),
        create_code_review_test_data(
            repository_url="https://github.com/test/repo2",
            standard_sets=[]
        )
    ]
    
    # Modify timestamps after creation - newer first for descending sort
    mock_reviews[0]["created_at"] = datetime.fromisoformat("2024-01-02T00:00:00")  # Newer
    mock_reviews[1]["created_at"] = datetime.fromisoformat("2024-01-01T00:00:00")  # Older
    
    # Properly mock cursor operations
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_reviews)
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    code_reviews_collection.find = MagicMock(return_value=mock_cursor)
    
    # When: Get all reviews request is made
    response = await async_client.get("/api/v1/code-reviews")
    
    # Then: Verify response and sorting
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    # Verify descending sort by created_at (newer first)
    assert data[0]["created_at"] > data[1]["created_at"]
    mock_cursor.sort.assert_called_once_with("created_at", -1)

async def test_get_all_code_reviews_filter_validation(
    async_client,
    setup_service
):
    """Test retrieving code reviews with invalid filter parameters."""
    # Given: Invalid query parameters
    _, code_reviews_collection, _ = setup_service
    
    # Mock find operation to not be called (should fail validation first)
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    code_reviews_collection.find = MagicMock(return_value=mock_cursor)
    
    # When: Get request is made with invalid filter
    response = await async_client.get("/api/v1/code-reviews?status=INVALID_STATUS")
    
    # Then: Verify error response
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "detail" in data
    assert any("status" in error["loc"] for error in data["detail"])

# Additional Test Cases - Get Single Code Review
async def test_get_code_review_by_id_with_relationships(
    async_client,
    setup_service
):
    """Test retrieving a code review with related data."""
    # Given: Code review with related standard sets
    _, code_reviews_collection, _ = setup_service
    standard_sets = [
        create_standard_set_reference(str(ObjectId())),
        create_standard_set_reference(str(ObjectId()))
    ]
    mock_review = create_code_review_test_data(
        repository_url="https://github.com/test/repo",
        standard_sets=standard_sets
    )
    code_reviews_collection.find_one = AsyncMock(return_value=mock_review)
    
    # When: Get specific review request is made
    response = await async_client.get(f"/api/v1/code-reviews/{str(mock_review['_id'])}")
    
    # Then: Verify response with relationships
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["standard_sets"]) == len(standard_sets)
    for i, standard_set in enumerate(data["standard_sets"]):
        assert standard_set["_id"] == str(standard_sets[i]["_id"])
        assert standard_set["name"] == standard_sets[i]["name"]

async def test_get_code_review_by_id_malformed_id(
    async_client,
    setup_service
):
    """Test get code review with malformed ObjectId."""
    # Given: Malformed ObjectId
    malformed_id = "not-an-object-id-at-all"
    
    # When: Get request is made with malformed ID
    response = await async_client.get(f"/api/v1/code-reviews/{malformed_id}")
    
    # Then: Verify bad request response
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Invalid ObjectId format" in data["detail"]
    assert malformed_id in data["detail"]

async def test_get_code_review_by_id_partial_failure(
    async_client,
    setup_service
):
    """Test get code review when some related data is missing."""
    # Given: Code review with missing related data
    _, code_reviews_collection, _ = setup_service
    mock_review = create_code_review_test_data(
        repository_url="https://github.com/test/repo",
        standard_sets=[{"_id": ObjectId(), "name": "Missing Set"}]
    )
    code_reviews_collection.find_one = AsyncMock(return_value=mock_review)
    
    # When: Get specific review request is made
    response = await async_client.get(f"/api/v1/code-reviews/{str(mock_review['_id'])}")
    
    # Then: Verify response still returns available data
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["_id"] == str(mock_review["_id"])
    assert data["repository_url"] == mock_review["repository_url"]
    assert len(data["standard_sets"]) == 1 