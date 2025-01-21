"""Integration tests for the code review retrieval endpoint.

This module contains integration tests that verify the functionality of:
1. Retrieving a code review by ID
2. Handling various ID formats and validation
3. Error handling for invalid IDs and database failures
4. PyObjectId model validation and schema generation
"""
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from src.models.code_review import ReviewStatus, PyObjectId
from bson import ObjectId
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_get_code_review_by_id_returns_correct_review(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful retrieval of a code review by ID.
    
    Given: A code review exists in the database
    When: Requesting the code review by its ID
    Then: Should return 200 with the correct review data
    """
    # Given
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.COMPLETED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    test_review['_id'] = str(result.inserted_id)

    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.get(
            f"/api/v1/code-reviews/{test_review['_id']}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["repository_url"] == test_review["repository_url"]
    assert data["_id"] == test_review["_id"]


def test_get_code_review_by_id_rejects_invalid_id_format(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test validation of ID format.
    
    Given: An invalid ID format
    When: Requesting a code review with that ID
    Then: Should return 400 with validation error
    """
    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.get("/api/v1/code-reviews/invalid-id")

    # Then
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_py_object_id_validates_correct_format() -> None:
    """
    Test PyObjectId validation with valid input.
    
    Given: A valid ObjectId
    When: Creating a PyObjectId from it
    Then: Should create object with correct string representation
    """
    # Given
    obj_id = ObjectId()
    
    # When
    py_obj_id = PyObjectId(obj_id)
    
    # Then
    assert str(py_obj_id) == str(obj_id)


def test_get_code_review_by_id_handles_database_errors(
    test_app: FastAPI,
    test_client: TestClient
) -> None:
    """
    Test error handling for database failures.
    
    Given: Database connection fails
    When: Requesting a code review by ID
    Then: Should return 500 with error details
    """
    # Given
    async def mock_get_database():
        raise Exception("Database connection error")

    # When
    with patch('src.api.v1.code_reviews.get_database', mock_get_database):
        response = test_client.get(
            "/api/v1/code-reviews/507f1f77bcf86cd799439011")

    # Then
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_get_code_review_accepts_string_id(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test support for string ID format.
    
    Given: A code review with string ID exists in database
    When: Requesting the code review using that ID
    Then: Should return 200 with correct review data
    """
    # Given
    standard_set_id = ObjectId()
    standard_set = {
        "_id": standard_set_id,
        "name": "Security Standards",
        "description": "Security standards for code review"
    }
    await mock_mongodb.standard_sets.insert_one(standard_set)

    test_review = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "repository_url": "https://github.com/example/repo1",
        "standard_sets": [str(standard_set_id)],
        "status": ReviewStatus.COMPLETED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await mock_mongodb.code_reviews.insert_one(test_review)

    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.get(f"/api/v1/code-reviews/{str(test_review['_id'])}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["repository_url"] == test_review["repository_url"]
    assert data["status"] == test_review["status"]
    assert len(data["standard_sets"]) == 1
    assert data["standard_sets"][0]["name"] == "Security Standards"


def test_py_object_id_handles_validation_edge_cases() -> None:
    """
    Test PyObjectId validation with edge cases.
    
    Given: Various invalid and valid ID formats
    When: Validating each format
    Then: Should correctly handle each case
    """
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
async def test_get_code_review_returns_404_when_not_found(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test handling of non-existent reviews.
    
    Given: No code review exists in database
    When: Requesting a code review with valid but non-existent ID
    Then: Should return 404 with not found message
    """
    # Given
    valid_id = ObjectId()  # Create a valid but non-existent ID

    # When
    with patch('src.database.db', mock_mongodb):
        # The mock database will naturally return None for a non-existent ID
        response = test_client.get(f"/api/v1/code-reviews/{str(valid_id)}")

    # Then
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_py_object_id_generates_correct_json_schema() -> None:
    """
    Test PyObjectId JSON schema generation.
    
    Given: A PyObjectId class
    When: Generating its JSON schema
    Then: Should return correct schema with string type and pattern
    """
    # Given
    from pydantic.json_schema import GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue

    class MockHandler(GetJsonSchemaHandler):
        def __init__(self):
            pass

        def resolve_ref_schema(self, schema):
            return schema

    # When
    schema = PyObjectId.__get_pydantic_json_schema__(None, MockHandler())

    # Then
    assert isinstance(schema, dict)
    assert schema["type"] == "string"
    assert schema["pattern"] == "^[0-9a-fA-F]{24}$" 


@pytest.mark.asyncio
async def test_get_code_review_includes_compliance_report_with_standard_set_name(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test that compliance reports include standard set names.
    
    Given: A code review with compliance reports exists in database
    When: Requesting the code review
    Then: Should return 200 with compliance reports containing standard set names
    """
    # Given
    standard_set_id = ObjectId()
    standard_set = {
        "_id": standard_set_id,
        "name": "Security Standards",
        "description": "Security standards for code review"
    }
    await mock_mongodb.standard_sets.insert_one(standard_set)

    test_review = {
        "_id": ObjectId(),
        "repository_url": "https://github.com/example/repo1",
        "standard_sets": [str(standard_set_id)],
        "status": ReviewStatus.COMPLETED,
        "compliance_reports": [{
            "id": str(standard_set_id),
            "file": "report.txt",
            "report": "Test report content",
            "standard_set_name": "Security Standards"
        }],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await mock_mongodb.code_reviews.insert_one(test_review)

    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.get(f"/api/v1/code-reviews/{str(test_review['_id'])}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data["compliance_reports"]) == 1
    report = data["compliance_reports"][0]
    assert report["id"] == str(standard_set_id)
    assert report["standard_set_name"] == "Security Standards"
    assert report["file"] == "report.txt"
    assert report["report"] == "Test report content"