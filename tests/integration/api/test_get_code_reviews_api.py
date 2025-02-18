"""Integration tests for code review Get endpoints.

Tests cover the code review Get API endpoints functionality while mocking
MongoDB interactions."""
import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from fastapi import status
from bson import ObjectId
from datetime import datetime
from src.main import app
from src.api.dependencies import get_code_review_service
from src.services.code_review_service import CodeReviewService
from src.repositories.code_review_repo import CodeReviewRepository
from tests.utils.test_data import (
    create_code_review_test_data,
    create_code_review_list_test_data,
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
def setup_list_cursor(mock_docs=None):
    """Helper fixture to setup cursor for list operations."""
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_docs or [])
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    return mock_cursor

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