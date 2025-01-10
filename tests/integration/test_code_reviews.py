"""Integration tests for code reviews endpoints."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from src.models.code_review import ReviewStatus


@pytest.mark.asyncio
async def test_get_code_reviews(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test getting all code reviews."""
    # Test data
    test_reviews = [
        {
            "repository_url": "https://github.com/example/repo1",
            "status": ReviewStatus.COMPLETED,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "repository_url": "https://github.com/example/repo2",
            "status": ReviewStatus.STARTED,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]

    # Insert test data
    await mock_mongodb.code_reviews.insert_many(test_reviews)

    # Patch the database connection
    with patch('src.database.db', mock_mongodb):
        # Make request to get all code reviews
        response = test_client.get("/api/v1/code-reviews")

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["repository_url"] == test_reviews[0]["repository_url"]
    assert data[1]["repository_url"] == test_reviews[1]["repository_url"]


@pytest.mark.asyncio
async def test_get_code_review_by_id(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test getting a code review by ID."""
    # Test data
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.COMPLETED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    # Insert test data
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    test_review['_id'] = str(result.inserted_id)

    # Patch the database connection
    with patch('src.database.db', mock_mongodb):
        # Make request to get the code review by ID
        response = test_client.get(
            f"/api/v1/code-reviews/{test_review['_id']}")

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["repository_url"] == test_review["repository_url"]
    assert data["_id"] == test_review["_id"]


@pytest.mark.asyncio
async def test_create_code_review(
    test_app: FastAPI,
    test_client: TestClient,
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
        response = test_client.post("/api/v1/code-reviews", json=test_review)

    # Assert response
    assert response.status_code == 201
    data = response.json()
    assert data["repository_url"] == test_review["repository_url"]
    assert "_id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["status"] == ReviewStatus.STARTED


def test_create_code_review_invalid_input(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test creating a code review with invalid input."""
    # Test data with missing required field
    test_review = {}

    # Patch the database connection
    with patch('src.database.db', mock_mongodb):
        # Make request to create a code review
        response = test_client.post("/api/v1/code-reviews", json=test_review)

    # Assert response
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_py_object_id_json_schema() -> None:
    """Test PyObjectId JSON schema."""
    from src.models.code_review import PyObjectId
    from bson import ObjectId

    # Test valid ObjectId
    obj_id = ObjectId()
    py_obj_id = PyObjectId(obj_id)
    assert str(py_obj_id) == str(obj_id)


@pytest.mark.asyncio
async def test_create_code_review_with_extra_fields(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test creating a code review with extra fields."""
    test_review = {
        "repository_url": "https://github.com/example/new-repo",
        "extra_field": "should be ignored"
    }

    with patch('src.database.db', mock_mongodb):
        response = test_client.post("/api/v1/code-reviews", json=test_review)

    assert response.status_code == 201
    data = response.json()
    assert "extra_field" not in data
    assert data["repository_url"] == test_review["repository_url"]


def test_get_code_review_by_id_error(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test error handling when getting a code review by ID."""
    with patch('src.database.db', mock_mongodb):
        # Test with invalid ObjectId format
        response = test_client.get("/api/v1/code-reviews/invalid-id")

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_py_object_id_validation() -> None:
    """Test PyObjectId validation."""
    from src.models.code_review import PyObjectId
    from bson import ObjectId

    # Test valid ObjectId
    obj_id = ObjectId()
    py_obj_id = PyObjectId(obj_id)
    assert str(py_obj_id) == str(obj_id)


def test_database_error_handling(
    test_app: FastAPI,
    test_client: TestClient
) -> None:
    """Test database error handling in endpoints."""

    # Mock the database connection to raise an exception
    async def mock_get_database():
        raise Exception("Database connection error")

    with patch('src.api.v1.code_reviews.get_database', mock_get_database):
        # Test error handling in get_code_review
        response = test_client.get(
            "/api/v1/code-reviews/507f1f77bcf86cd799439011")

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_get_code_reviews_with_invalid_id(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test get_code_reviews with invalid _id in database."""
    # Setup test data with invalid _id
    test_reviews = [
        {
            "_id": "",  # Invalid _id
            "repository_url": "https://github.com/example/repo1",
            "status": ReviewStatus.COMPLETED,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]

    await mock_mongodb.code_reviews.insert_many(test_reviews)

    with patch('src.database.db', mock_mongodb):
        response = test_client.get("/api/v1/code-reviews")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Invalid review should be filtered out


def test_get_code_reviews_error(
    test_app: FastAPI,
    test_client: TestClient
) -> None:
    """Test error handling in get_code_reviews endpoint."""

    # Mock the database connection to raise an exception
    async def mock_get_database():
        raise Exception("Database error")

    with patch('src.api.v1.code_reviews.get_database', mock_get_database):
        response = test_client.get("/api/v1/code-reviews")

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


def test_py_object_id_json_schema_generation() -> None:
    """Test JSON schema generation for PyObjectId."""
    from src.models.code_review import PyObjectId
    from pydantic.json_schema import GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue

    # Create a mock handler
    class MockHandler(GetJsonSchemaHandler):
        def __init__(self):
            pass

    schema = PyObjectId.__get_pydantic_json_schema__(None, MockHandler())
    assert isinstance(schema, dict)
    assert schema["type"] == "string"
    assert schema["pattern"] == "^[0-9a-fA-F]{24}$"


@pytest.mark.asyncio
async def test_get_code_review_string_id_fallback(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test getting a code review with string ID fallback."""
    test_review = {
        "_id": "507f1f77bcf86cd799439011",  # Valid ObjectId as string
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.COMPLETED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    await mock_mongodb.code_reviews.insert_one(test_review)

    with patch('src.database.db', mock_mongodb):
        response = test_client.get(
            f"/api/v1/code-reviews/{test_review['_id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["_id"] == test_review["_id"]


def test_py_object_id_validation_edge_cases() -> None:
    """Test PyObjectId validation edge cases."""
    from src.models.code_review import PyObjectId

    # Test invalid type
    with pytest.raises(ValueError, match="Invalid ObjectId"):
        PyObjectId.validate(123)

    # Test invalid string format
    with pytest.raises(ValueError, match="Invalid ObjectId"):
        PyObjectId.validate("not-an-object-id")

    # Test valid string format
    valid_id = "507f1f77bcf86cd799439011"
    assert PyObjectId.validate(valid_id) == valid_id


@pytest.mark.asyncio
async def test_get_code_review_not_found(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test 404 response when code review is not found."""
    valid_id = "507f1f77bcf86cd799439011"

    with patch('src.database.db', mock_mongodb):
        response = test_client.get(f"/api/v1/code-reviews/{valid_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Code review not found"


def test_py_object_id_json_schema_generation() -> None:
    """Test PyObjectId JSON schema generation."""
    from src.models.code_review import PyObjectId
    from pydantic.json_schema import GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue

    # Create a mock handler
    class MockHandler(GetJsonSchemaHandler):
        def __init__(self):
            pass

    schema = PyObjectId.__get_pydantic_json_schema__(None, MockHandler())
    assert isinstance(schema, dict)
    assert schema["type"] == "string"
    assert schema["pattern"] == "^[0-9a-fA-F]{24}$"
