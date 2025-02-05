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

# Test Cases - Create Code Review
async def test_create_code_review_success(
    async_client,
    mock_database_setup,
    mock_collections,
    valid_code_review_data
):
    """Test successful creation of a code review."""
    # Given: Valid code review data
    code_reviews_collection, standard_sets_collection = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    mock_database_setup.standard_sets = standard_sets_collection
    standard_set = create_standard_set_reference(valid_code_review_data["standard_sets"][0])
    standard_sets_collection.find_one = AsyncMock(return_value=standard_set)
    mock_doc = create_code_review_test_data(
        repository_url=valid_code_review_data["repository_url"],
        standard_sets=[standard_set]
    )
    insert_result = AsyncMock()
    insert_result.inserted_id = mock_doc["_id"]
    code_reviews_collection.insert_one = AsyncMock(return_value=insert_result)
    code_reviews_collection.find_one = AsyncMock(return_value=mock_doc)
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
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
    mock_database_setup,
    mock_collections,
    invalid_code_review_data
):
    """Test code review creation with invalid input data."""
    # Given: Invalid test data and setup service
    code_reviews_collection, _ = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
    # When: Create request is made with invalid data
    with patch('src.services.code_review_service.Process'):
        response = await async_client.post("/api/v1/code-reviews", json=invalid_code_review_data)
    
    # Then: Verify validation error response
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)  # FastAPI validation error format

async def test_create_code_review_invalid_standard_set(
    async_client,
    mock_database_setup,
    mock_collections,
    valid_code_review_data
):
    """Test code review creation with non-existent standard set."""
    # Given: Setup with non-existent standard set
    code_reviews_collection, standard_sets_collection = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    mock_database_setup.standard_sets = standard_sets_collection
    standard_sets_collection.find_one = AsyncMock(return_value=None)
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
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
    mock_database_setup,
    mock_collections,
    valid_code_review_data
):
    """Test code review creation with database error."""
    # Given: Setup with database error
    code_reviews_collection, standard_sets_collection = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    mock_database_setup.standard_sets = standard_sets_collection
    standard_set = create_standard_set_reference(valid_code_review_data["standard_sets"][0])
    standard_sets_collection.find_one = AsyncMock(return_value=standard_set)
    code_reviews_collection.insert_one = AsyncMock(
        side_effect=Exception("Database error")
    )
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
    # When: Create request is made
    with patch('src.services.code_review_service.Process') as mock_process:
        response = await async_client.post("/api/v1/code-reviews", json=valid_code_review_data)
        
        # Then: Verify error response and no process creation
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Error creating code review" in data["detail"]
        assert "Database error" in data["detail"]
        mock_process.assert_not_called()

# Test Cases - Get All Code Reviews
async def test_get_all_code_reviews_success(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test successful retrieval of all code reviews."""
    # Given: Code reviews exist
    code_reviews_collection, _ = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    mock_reviews = [create_code_review_list_test_data() for _ in range(2)]
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_reviews)
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    code_reviews_collection.find = MagicMock(return_value=mock_cursor)
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
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

async def test_get_all_code_reviews_db_error(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test get all code reviews with database error."""
    # Given: Mock database error
    code_reviews_collection, _ = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(side_effect=Exception("Database error"))
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    code_reviews_collection.find = MagicMock(return_value=mock_cursor)
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
    # When: Get all reviews request is made
    response = await async_client.get("/api/v1/code-reviews")
    
    # Then: Verify error response
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert "Error fetching code reviews" in data["detail"]
    assert "Database error" in data["detail"]

async def test_get_all_code_reviews_empty(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test successful retrieval of empty code reviews list."""
    # Given: Setup mock data for empty list
    code_reviews_collection, _ = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    code_reviews_collection.find = MagicMock(return_value=mock_cursor)
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
    # When: Get all reviews request is made
    response = await async_client.get("/api/v1/code-reviews")
    
    # Then: Verify empty response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

# Test Cases - Get Code Review by ID
async def test_get_code_review_by_id_success(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test successful retrieval of a specific code review."""
    # Given: Setup mock data
    code_reviews_collection, _ = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    standard_set_id = str(ObjectId())
    standard_set = create_standard_set_reference(standard_set_id)
    mock_review = create_code_review_test_data(
        repository_url="https://github.com/test/repo",
        standard_sets=[standard_set]
    )
    code_reviews_collection.find_one = AsyncMock(return_value=mock_review)
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
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
    for i, standard_set_data in enumerate(data["standard_sets"]):
        mock_standard_set = mock_review["standard_sets"][i]
        assert standard_set_data["_id"] == mock_standard_set["id"]
        assert standard_set_data["name"] == mock_standard_set["name"]
    assert isinstance(data["compliance_reports"], list)
    assert "created_at" in data
    assert "updated_at" in data

async def test_get_code_review_not_found(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test get code review with non-existent ID."""
    # Given: Mock non-existent review
    code_reviews_collection, _ = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    code_reviews_collection.find_one = AsyncMock(return_value=None)
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    test_id = str(ObjectId())
    
    # When: Get request is made with non-existent ID
    response = await async_client.get(f"/api/v1/code-reviews/{test_id}")
    
    # Then: Verify not found response
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert f"Code review {test_id} not found" in data["detail"]

async def test_get_code_review_invalid_id(
    async_client,
    mock_database_setup,
    mock_collections
):
    """Test get code review with invalid ID format."""
    # Given: Invalid ID and setup service
    code_reviews_collection, _ = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
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
    mock_database_setup,
    mock_collections
):
    """Test get code review with database error."""
    # Given: Mock database error
    code_reviews_collection, _ = mock_collections
    mock_database_setup.code_reviews = code_reviews_collection
    
    # Mock find_one operation with error
    code_reviews_collection.find_one = AsyncMock(
        side_effect=Exception("Database error")
    )
    
    # Setup repository and service
    repo = CodeReviewRepository(code_reviews_collection)
    service = CodeReviewService(mock_database_setup, repo)
    app.dependency_overrides[get_code_review_service] = lambda: service
    
    test_id = str(ObjectId())
    
    # When: Get request is made
    response = await async_client.get(f"/api/v1/code-reviews/{test_id}")
    
    # Then: Verify error response
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert "Error fetching code review" in data["detail"]
    assert "Database error" in data["detail"] 