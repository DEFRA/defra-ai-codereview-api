"""Integration tests for the classification endpoints.

This module contains integration tests that verify the functionality of:
1. Creating new classifications
2. Listing all classifications
3. Deleting classifications
4. Error handling for various scenarios
"""
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from bson import ObjectId
from src.models.classification import Classification
from unittest.mock import patch
from fastapi import HTTPException, status


@pytest.mark.asyncio
async def test_create_classification_succeeds_with_valid_input(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful creation of a classification.
    
    Given: A valid classification data
    When: Creating a new classification
    Then: Response should be 201 with correct classification data
    """
    # Given
    test_classification = {
        "name": "Security"
    }

    # When
    response = test_client.post("/api/v1/classifications", json=test_classification)

    # Then
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == test_classification["name"]
    assert "_id" in data


def test_create_classification_fails_with_missing_required_fields(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test validation of required fields.
    
    Given: A request body missing required fields
    When: Creating a new classification
    Then: Response should be 422 with validation error details
    """
    # Given
    test_classification = {
        # Missing name
    }

    # When
    response = test_client.post("/api/v1/classifications", json=test_classification)

    # Then
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_list_classifications_returns_all_items(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test listing all classifications.
    
    Given: Multiple classifications in the database
    When: Requesting all classifications
    Then: Response should include all classifications
    """
    # Given
    # Clear existing data
    await mock_mongodb.classifications.delete_many({})
    
    test_classifications = [
        {
            "_id": ObjectId(),
            "name": "Security",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "_id": ObjectId(),
            "name": "Performance",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]
    
    for classification in test_classifications:
        await mock_mongodb.classifications.insert_one(classification)

    # When
    response = test_client.get("/api/v1/classifications")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(test_classifications)
    assert all(item["name"] in ["Security", "Performance"] for item in data)


@pytest.mark.asyncio
async def test_delete_classification_succeeds_with_valid_id(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful deletion of a classification.
    
    Given: A valid classification ID
    When: Deleting the classification
    Then: Response should confirm deletion
    """
    # Given
    # Clear existing data
    await mock_mongodb.classifications.delete_many({})
    
    test_classification = {
        "_id": ObjectId(),
        "name": "Test",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await mock_mongodb.classifications.insert_one(test_classification)
    classification_id = str(test_classification["_id"])

    # When
    response = test_client.delete(f"/api/v1/classifications/{classification_id}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Verify deletion
    remaining = await mock_mongodb.classifications.find_one({"_id": ObjectId(classification_id)})
    assert remaining is None


@pytest.mark.asyncio
async def test_delete_classification_fails_with_invalid_id(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test deletion with invalid ID.
    
    Given: An invalid classification ID
    When: Attempting to delete the classification
    Then: Response should be 400 with error message
    """
    # Given
    invalid_id = "invalid-id"

    # When
    response = test_client.delete(f"/api/v1/classifications/{invalid_id}")

    # Then
    assert response.status_code == 400
    data = response.json()
    assert "Invalid ObjectId format" in data["detail"]


@pytest.mark.asyncio
async def test_delete_classification_fails_with_nonexistent_id(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test deletion with nonexistent ID.
    
    Given: A valid but nonexistent classification ID
    When: Attempting to delete the classification
    Then: Response should be 404 with error message
    """
    # Given
    # Clear existing data
    await mock_mongodb.classifications.delete_many({})
    
    nonexistent_id = str(ObjectId())

    # When
    response = test_client.delete(f"/api/v1/classifications/{nonexistent_id}")

    # Then
    assert response.status_code == 404
    data = response.json()
    assert "Classification not found" in data["detail"]


@pytest.mark.asyncio
async def test_create_classification_handles_database_error(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test error handling when database operation fails during creation.
    
    Given: A database that raises an error during insert
    When: Creating a new classification
    Then: Should return 400 with error message
    """
    # Given
    test_classification = {
        "name": "Security"
    }
    
    # When
    with patch('src.repositories.classification_repo.ClassificationRepository.create') as mock_create:
        mock_create.side_effect = Exception("Database error")
        response = test_client.post("/api/v1/classifications", json=test_classification)
    
    # Then
    assert response.status_code == 400
    data = response.json()
    assert "Database error" in data["detail"]


@pytest.mark.asyncio
async def test_list_classifications_handles_database_error(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test error handling when database operation fails during listing.
    
    Given: A database that raises an error during find operation
    When: Requesting all classifications
    Then: Should return 500 with error message
    """
    # When
    with patch('src.repositories.classification_repo.ClassificationRepository.get_all') as mock_get_all:
        mock_get_all.side_effect = Exception("Database error")
        response = test_client.get("/api/v1/classifications")
    
    # Then
    assert response.status_code == 500
    data = response.json()
    assert "Failed to retrieve classifications" in data["detail"]


@pytest.mark.asyncio
async def test_delete_classification_handles_database_error(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test error handling when database operation fails during deletion.
    
    Given: A database that raises an error during delete operation
    When: Deleting a classification
    Then: Should return 500 with error message
    """
    # Given
    test_id = str(ObjectId())
    
    # When
    with patch('src.repositories.classification_repo.ClassificationRepository.delete') as mock_delete:
        mock_delete.side_effect = Exception("Database error")
        response = test_client.delete(f"/api/v1/classifications/{test_id}")
    
    # Then
    assert response.status_code == 500
    data = response.json()
    assert "Failed to delete classification" in data["detail"]


@pytest.mark.asyncio
async def test_delete_classification_reraises_http_exception(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test that HTTPExceptions are re-raised during deletion.
    
    Given: A repository that raises an HTTPException
    When: Deleting a classification
    Then: Should pass through the original HTTPException
    """
    # Given
    test_id = str(ObjectId())
    http_error = HTTPException(status_code=status.HTTP_418_IM_A_TEAPOT, detail="Test HTTP error")
    
    # When
    with patch('src.repositories.classification_repo.ClassificationRepository.delete') as mock_delete:
        mock_delete.side_effect = http_error
        response = test_client.delete(f"/api/v1/classifications/{test_id}")
    
    # Then
    assert response.status_code == status.HTTP_418_IM_A_TEAPOT
    data = response.json()
    assert "Test HTTP error" in data["detail"]


@pytest.mark.asyncio
async def test_delete_classification_handles_not_found_error(
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test error handling when a "Classification not found" error is raised during deletion.
    
    Given: A repository that raises an error with "Classification not found" message
    When: Deleting a classification
    Then: Should return 404 with not found message
    """
    # Given
    test_id = str(ObjectId())
    
    # When
    with patch('src.repositories.classification_repo.ClassificationRepository.delete') as mock_delete:
        mock_delete.side_effect = Exception("Classification not found")
        response = test_client.delete(f"/api/v1/classifications/{test_id}")
    
    # Then
    assert response.status_code == 404
    data = response.json()
    assert "Classification not found" in data["detail"] 