"""Integration tests for classification endpoints.

Tests cover the classification API endpoints functionality while mocking
MongoDB interactions."""
import pytest
from fastapi import status
from bson import ObjectId
from unittest.mock import MagicMock, AsyncMock
from tests.utils.test_data import valid_classification_data, create_db_document

# Test Cases - Create
async def test_create_classification_success(
    async_client,
    mock_database_setup,
    mock_mongodb_operations,
    valid_classification_data
):
    # Given: A valid classification payload
    mock_mongodb_operations("classifications", "find_one", return_value=None)
    mock_mongodb_operations("classifications", "insert_one")
    
    # When: POST request is made
    response = await async_client.post(
        "/api/v1/classifications",
        json=valid_classification_data
    )
    
    # Then: Returns 201 with created classification
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == valid_classification_data["name"]
    assert "_id" in data
    
    # Verify database interactions
    mock_database_setup.classifications.find_one.assert_called_once()
    mock_database_setup.classifications.insert_one.assert_called_once()

async def test_create_classification_failure(
    async_client,
    mock_database_setup,
    valid_classification_data
):
    # Given: Database operation fails
    mock_database_setup.classifications.insert_one.side_effect = Exception("Database error")
    
    # When: POST request is made
    response = await async_client.post(
        "/api/v1/classifications",
        json=valid_classification_data
    )
    
    # Then: Returns 400 with error message
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Database error" in response.json()["detail"]

# Test Cases - List
async def test_list_classifications_success(
    async_client,
    mock_database_setup,
    valid_classification_data
):
    # Given: Existing classifications in the database
    mock_doc = create_db_document(**valid_classification_data)
    mock_find = MagicMock()
    mock_find.to_list = AsyncMock(return_value=[mock_doc])
    mock_database_setup.classifications.find = MagicMock(return_value=mock_find)
    
    # When: GET request is made
    response = await async_client.get("/api/v1/classifications")
    
    # Then: Returns 200 with list of classifications
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == valid_classification_data["name"]
    assert "_id" in data[0]
    assert "created_at" in data[0]
    assert "updated_at" in data[0]

async def test_list_classifications_failure(
    async_client,
    mock_database_setup
):
    # Given: Database operation fails
    mock_database_setup.classifications.find.side_effect = Exception("Database error")
    
    # When: GET request is made
    response = await async_client.get("/api/v1/classifications")
    
    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to retrieve classifications" in response.json()["detail"]

# Test Cases - Delete
async def test_delete_classification_success(
    async_client,
    mock_mongodb_operations
):
    # Given: Valid classification ID
    classification_id = str(ObjectId())
    mock_mongodb_operations("classifications", "delete_one", deleted_count=1)
    
    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/classifications/{classification_id}")
    
    # Then: Returns 200 with success message
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"

async def test_delete_classification_not_found(
    async_client,
    mock_mongodb_operations
):
    # Given: Non-existent classification ID
    classification_id = str(ObjectId())
    mock_mongodb_operations("classifications", "delete_one", deleted_count=0)
    
    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/classifications/{classification_id}")
    
    # Then: Returns 404 with not found message
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Classification not found" in response.json()["detail"]

async def test_delete_classification_invalid_id(
    async_client,
    mock_database_setup
):
    # Given: Invalid ObjectId format
    invalid_id = "invalid-id"
    
    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/classifications/{invalid_id}")
    
    # Then: Returns 400 with invalid format message
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid ObjectId format" in response.json()["detail"]
    mock_database_setup.classifications.delete_one.assert_not_called()

async def test_delete_classification_server_error(
    async_client,
    mock_database_setup
):
    # Given: Database operation throws unexpected error
    valid_id = str(ObjectId())
    mock_database_setup.classifications.delete_one.side_effect = Exception("Unexpected database error")
    
    # When: DELETE request is made
    response = await async_client.delete(f"/api/v1/classifications/{valid_id}")
    
    # Then: Returns 500 with error message
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to delete classification" in response.json()["detail"]
    mock_database_setup.classifications.delete_one.assert_called_once()