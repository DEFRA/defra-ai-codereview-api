"""Integration tests for get code review by ID endpoint."""
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from src.models.code_review import ReviewStatus, PyObjectId
from bson import ObjectId


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