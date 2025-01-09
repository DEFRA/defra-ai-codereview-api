"""Integration tests for code review endpoints."""
import pytest
from httpx import AsyncClient
from fastapi import FastAPI, status
from mongomock_motor import AsyncMongoMockClient
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock, AsyncMock
from src.database import get_database
from src.models.code_review import ReviewStatus, PyObjectId
from bson import ObjectId

@pytest.mark.asyncio
async def test_get_code_reviews(
    test_app: FastAPI,
    test_client: AsyncClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test retrieving all code reviews."""
    # Setup test data
    test_reviews = [
        {
            "_id": "507f1f77bcf86cd799439011",
            "repository_url": "https://github.com/example/repo1",
            "status": ReviewStatus.COMPLETED,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        },
        {
            "_id": "507f1f77bcf86cd799439012",
            "repository_url": "https://github.com/example/repo2",
            "status": ReviewStatus.STARTED,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
    ]
    
    # Insert test data into mock database
    await mock_mongodb.code_reviews.insert_many(test_reviews)
    
    # Patch the database connection
    with patch('src.database.db', mock_mongodb):
        # Make request to get all code reviews
        response = await test_client.get("/api/v1/code-reviews")
        
        # Assert response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["repository_url"] == "https://github.com/example/repo1"
        assert data[1]["repository_url"] == "https://github.com/example/repo2"
        assert data[0]["status"] == ReviewStatus.COMPLETED
        assert data[1]["status"] == ReviewStatus.STARTED

@pytest.mark.asyncio
async def test_get_code_review_by_id(
    test_app: FastAPI,
    test_client: AsyncClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test retrieving a single code review by ID."""
    # Setup test data
    test_review = {
        "_id": "507f1f77bcf86cd799439011",
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.COMPLETED,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    
    # Insert test data into mock database
    await mock_mongodb.code_reviews.insert_one(test_review)
    
    # Patch the database connection
    with patch('src.database.db', mock_mongodb):
        # Test successful retrieval
        response = await test_client.get(f"/api/v1/code-reviews/{test_review['_id']}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["repository_url"] == test_review["repository_url"]
        assert data["status"] == ReviewStatus.COMPLETED
        
        # Test non-existent ID
        response = await test_client.get("/api/v1/code-reviews/507f1f77bcf86cd799439999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Test invalid ID format
        response = await test_client.get("/api/v1/code-reviews/invalid-id")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
async def test_create_code_review(
    test_app: FastAPI,
    test_client: AsyncClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test creating a new code review."""
    # Test data
    test_review = {
        "repository_url": "https://github.com/example/new-repo"
    }
    
    # Patch the database connection
    with patch('src.database.db', mock_mongodb):
        # Make request to create a code review
        response = await test_client.post("/api/v1/code-reviews", json=test_review)
        
        # Assert response
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["repository_url"] == test_review["repository_url"]
        assert data["status"] == ReviewStatus.STARTED
        assert "_id" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Verify the review was saved in the database
        saved_review = await mock_mongodb.code_reviews.find_one({"repository_url": test_review["repository_url"]})
        assert saved_review is not None
        assert saved_review["repository_url"] == test_review["repository_url"]
        assert saved_review["status"] == ReviewStatus.STARTED

@pytest.mark.asyncio
async def test_create_code_review_invalid_input(
    test_app: FastAPI,
    test_client: AsyncClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test creating a code review with invalid input."""
    # Test data with missing required field
    test_review = {}
    
    # Patch the database connection
    with patch('src.database.db', mock_mongodb):
        # Make request to create a code review
        response = await test_client.post("/api/v1/code-reviews", json=test_review)
        
        # Assert response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_py_object_id_json_schema():
    """Test PyObjectId JSON schema generation."""
    schema = PyObjectId.__get_pydantic_json_schema__(None, None)
    assert schema == {"type": "string", "pattern": "^[0-9a-fA-F]{24}$"}

@pytest.mark.asyncio
async def test_create_code_review_with_extra_fields(
    test_app: FastAPI,
    test_client: AsyncClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test creating a code review with extra fields."""
    test_review = {
        "repository_url": "https://github.com/example/new-repo",
        "extra_field": "should be ignored"
    }
    
    with patch('src.database.db', mock_mongodb):
        response = await test_client.post("/api/v1/code-reviews", json=test_review)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["repository_url"] == test_review["repository_url"]
        assert "extra_field" not in data

@pytest.mark.asyncio
async def test_get_code_review_by_id_error(
    test_app: FastAPI,
    test_client: AsyncClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test error handling when getting a code review by ID."""
    with patch('src.database.db', mock_mongodb):
        # Test with invalid ObjectId format
        response = await test_client.get("/api/v1/code-reviews/invalid-id")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Test with non-existent ObjectId
        response = await test_client.get("/api/v1/code-reviews/507f1f77bcf86cd799439999")
        assert response.status_code == status.HTTP_404_NOT_FOUND 

def test_py_object_id_validation():
    """Test PyObjectId validation."""
    # Test valid ObjectId string
    valid_id = "507f1f77bcf86cd799439011"
    assert PyObjectId.validate(valid_id) == valid_id
    
    # Test valid ObjectId instance
    obj_id = ObjectId()
    assert PyObjectId.validate(obj_id) == str(obj_id)
    
    # Test invalid type
    with pytest.raises(ValueError, match="Invalid ObjectId"):
        PyObjectId.validate(123)
    
    # Test invalid ObjectId string
    with pytest.raises(ValueError, match="Invalid ObjectId"):
        PyObjectId.validate("invalid-id")

@pytest.mark.asyncio
async def test_database_error_handling(
    test_app: FastAPI,
    test_client: AsyncClient
) -> None:
    """Test database error handling in endpoints."""
    
    # Mock the database connection to raise an exception
    async def mock_get_database():
        raise Exception("Database connection error")
    
    with patch('src.api.v1.code_reviews.get_database', mock_get_database):
        # Test error handling in get_code_review
        response = await test_client.get("/api/v1/code-reviews/507f1f77bcf86cd799439011")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal server error" in response.json()["detail"]
        
        # Test error handling in create_code_review
        test_review = {"repository_url": "https://github.com/example/repo"}
        response = await test_client.post("/api/v1/code-reviews", json=test_review)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error creating code review" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_code_reviews_with_invalid_id(
    test_app: FastAPI,
    test_client: AsyncClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test get_code_reviews with invalid _id in database."""
    # Setup test data with invalid _id
    test_reviews = [
        {
            "_id": "",  # Invalid _id
            "repository_url": "https://github.com/example/repo1",
            "status": ReviewStatus.COMPLETED,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
    ]
    
    await mock_mongodb.code_reviews.insert_many(test_reviews)
    
    with patch('src.database.db', mock_mongodb):
        response = await test_client.get("/api/v1/code-reviews")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0  # Invalid review should be filtered out 

@pytest.mark.asyncio
async def test_get_code_reviews_error(
    test_app: FastAPI,
    test_client: AsyncClient
) -> None:
    """Test error handling in get_code_reviews endpoint."""
    
    # Mock the database connection to raise an exception
    async def mock_get_database():
        raise Exception("Database error")
    
    with patch('src.api.v1.code_reviews.get_database', mock_get_database):
        response = await test_client.get("/api/v1/code-reviews")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error fetching code reviews" in response.json()["detail"] 