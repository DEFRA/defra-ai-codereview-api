"""Integration tests for the standard sets endpoints."""
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from bson import ObjectId
from src.repositories.standard_set_repo import StandardSetRepository
from src.dependencies import get_database, get_standard_set_repo

@pytest.fixture
async def mock_mongodb():
    client = AsyncMongoMockClient()
    db = client.test_database
    return db

@pytest.mark.asyncio
async def test_create_standard_set_succeeds_with_valid_input(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test successful creation of a standard set."""
    # Given
    test_standard_set = {
        "name": "Security Standards",
        "repository_url": "https://github.com/org/security-standards",
        "custom_prompt": "Analyze code for security issues..."
    }

    # When
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    response = test_client.post("/api/v1/standard-sets", json=test_standard_set)
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 201
    created_set = response.json()
    assert created_set["name"] == test_standard_set["name"]
    assert created_set["repository_url"] == test_standard_set["repository_url"]
    assert created_set["custom_prompt"] == test_standard_set["custom_prompt"]
    assert "created_at" in created_set
    assert "updated_at" in created_set

@pytest.mark.asyncio
async def test_create_standard_set_replaces_existing_with_same_name(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test replacement of existing standard set."""
    # Given
    existing_set = {
        "name": "Security Standards",
        "repository_url": "https://github.com/org/old-security-standards",
        "custom_prompt": "Old prompt..."
    }

    # Clear any existing data
    await mock_mongodb["standard_sets"].delete_many({})
    
    # Insert and verify initial state
    await mock_mongodb["standard_sets"].insert_one(existing_set)
    initial_sets = await mock_mongodb["standard_sets"].find({}).to_list(length=None)
    assert len(initial_sets) == 1
    assert initial_sets[0]["repository_url"] == existing_set["repository_url"]

    new_set = {
        "name": "Security Standards",
        "repository_url": "https://github.com/org/new-security-standards",
        "custom_prompt": "New prompt..."
    }

    # When
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    response = test_client.post("/api/v1/standard-sets", json=new_set)
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 201
    updated_set = response.json()
    assert updated_set["name"] == new_set["name"]
    assert updated_set["repository_url"] == new_set["repository_url"]
    assert updated_set["custom_prompt"] == new_set["custom_prompt"]

    # Verify only one document exists and it's the updated one
    all_sets = await mock_mongodb["standard_sets"].find({}).to_list(length=None)
    assert len(all_sets) == 1
    assert all_sets[0]["repository_url"] == new_set["repository_url"]

@pytest.mark.asyncio
async def test_create_standard_set_fails_with_missing_required_fields(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test validation of required fields.
    
    Given: A request body missing required fields
    When: Creating a new standard set
    Then: Response should be 422 with validation error details
    """
    # Given
    test_standard_set = {
        # Missing required fields
        "custom_prompt": "Test prompt"
    }

    # When
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    response = test_client.post("/api/v1/standard-sets", json=test_standard_set)
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    validation_errors = data["detail"]
    assert any("name" in error["loc"] for error in validation_errors)
    assert any("repository_url" in error["loc"] for error in validation_errors) 

@pytest.mark.asyncio
async def test_verify_mock_database_isolation(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Verify that test data is isolated to mock database."""
    # Given
    test_standard_set = {
        "name": "Test Isolation Set",
        "repository_url": "https://github.com/org/test-isolation",
        "custom_prompt": "Test prompt"
    }

    # When using mock database
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    response = test_client.post("/api/v1/standard-sets", json=test_standard_set)
    
    # Then
    assert response.status_code == 201
    
    # Verify data exists in mock
    mock_result = await mock_mongodb["standard_sets"].find_one({"name": "Test Isolation Set"})
    assert mock_result is not None
    
    # Clear the mock override and verify isolation
    test_app.dependency_overrides.clear()
    
    # Make a new request to get data using real database
    response = test_client.get("/api/v1/standard-sets")
    assert response.status_code == 200
    
    # Check that the test data is not in the response
    real_data = response.json()
    assert not any(item["name"] == "Test Isolation Set" for item in real_data) 

@pytest.mark.asyncio
async def test_get_standard_set_by_id_basic(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test basic retrieval of a standard set."""
    # Given
    test_standard_set = {
        "_id": ObjectId(),
        "name": "Test Set",
        "repository_url": "https://github.com/test/repo",
        "custom_prompt": "Test prompt"
    }

    # Insert directly into collection
    await mock_mongodb.standard_sets.insert_one(test_standard_set)

    # When
    repo = StandardSetRepository(mock_mongodb.standard_sets)
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    test_app.dependency_overrides[get_standard_set_repo] = lambda: repo
    response = test_client.get(f"/api/v1/standard-sets/{str(test_standard_set['_id'])}")
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_delete_standard_set_basic(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test basic deletion of a standard set."""
    # Given
    test_standard_set = {
        "name": "Test Set",
        "repository_url": "https://github.com/test/repo",
        "custom_prompt": "Test prompt"
    }
    result = await mock_mongodb.standard_sets.insert_one(test_standard_set)
    
    # Create test standard
    test_standard = {
        "text": "Test standard",
        "repository_path": "/test/path",
        "standard_set_id": result.inserted_id,
        "classification_ids": []
    }
    await mock_mongodb.standards.insert_one(test_standard)
    
    # When
    repo = StandardSetRepository(mock_mongodb.standard_sets)
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    test_app.dependency_overrides[get_standard_set_repo] = lambda: repo
    response = test_client.delete(f"/api/v1/standard-sets/{str(result.inserted_id)}")
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    # Verify deletion
    remaining_set = await mock_mongodb.standard_sets.find_one({"_id": result.inserted_id})
    assert remaining_set is None

@pytest.mark.asyncio
async def test_get_standard_set_by_id_returns_complete_data(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful retrieval of a standard set with all associated data.
    
    Given: A standard set with associated standards exists in database
    When: Requesting the standard set by its ID
    Then: Should return 200 with complete standard set data including standards
    """
    # Given
    # Create test standard set
    test_standard_set = {
        "name": "Security Standards",
        "repository_url": "https://github.com/org/security-standards",
        "custom_prompt": "Test prompt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    set_result = await mock_mongodb.standard_sets.insert_one(test_standard_set)
    
    # Create associated standards
    test_standards = [
        {
            "text": "Standard 1",
            "repository_path": "/path/1",
            "standard_set_id": str(set_result.inserted_id),
            "classification_ids": [ObjectId(), ObjectId()]
        },
        {
            "text": "Standard 2",
            "repository_path": "/path/2",
            "standard_set_id": str(set_result.inserted_id),
            "classification_ids": []
        }
    ]
    await mock_mongodb.standards.insert_many(test_standards)

    # When
    repo = StandardSetRepository(mock_mongodb.standard_sets)
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    test_app.dependency_overrides[get_standard_set_repo] = lambda: repo
    response = test_client.get(f"/api/v1/standard-sets/{str(set_result.inserted_id)}")
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_standard_set["name"]
    assert data["repository_url"] == test_standard_set["repository_url"]
    assert data["custom_prompt"] == test_standard_set["custom_prompt"]
    assert len(data["standards"]) == 2
    assert any(s["text"] == "Standard 1" for s in data["standards"])
    assert any(s["text"] == "Standard 2" for s in data["standards"])

@pytest.mark.asyncio
async def test_get_standard_set_by_id_returns_404_when_not_found(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test handling of non-existent standard sets.
    
    Given: No standard set exists with the specified ID
    When: Requesting a standard set by that ID
    Then: Should return 404 with not found message
    """
    # Given
    non_existent_id = str(ObjectId())

    # When
    repo = StandardSetRepository(mock_mongodb.standard_sets)
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    test_app.dependency_overrides[get_standard_set_repo] = lambda: repo
    response = test_client.get(f"/api/v1/standard-sets/{non_existent_id}")
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 404
    data = response.json()
    assert "Standard set not found" in data["detail"]

@pytest.mark.asyncio
async def test_delete_standard_set_removes_all_associated_data(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful deletion of a standard set and all associated data.
    
    Given: A standard set with associated standards exists
    When: Deleting the standard set
    Then: Should delete the set and all associated standards
    """
    # Given
    # Create test standard set
    test_standard_set = {
        "name": "Security Standards",
        "repository_url": "https://github.com/org/security-standards",
        "custom_prompt": "Test prompt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    set_result = await mock_mongodb.standard_sets.insert_one(test_standard_set)
    
    # Create associated standards with classification references
    classification_id = ObjectId()
    test_standards = [
        {
            "text": "Standard 1",
            "repository_path": "/path/1",
            "standard_set_id": str(set_result.inserted_id),
            "classification_ids": [classification_id]
        },
        {
            "text": "Standard 2",
            "repository_path": "/path/2",
            "standard_set_id": str(set_result.inserted_id),
            "classification_ids": [classification_id]
        }
    ]
    await mock_mongodb.standards.insert_many(test_standards)
    
    # When
    repo = StandardSetRepository(mock_mongodb.standard_sets)
    repo.standards_collection = mock_mongodb.standards
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    test_app.dependency_overrides[get_standard_set_repo] = lambda: repo
    response = test_client.delete(f"/api/v1/standard-sets/{str(set_result.inserted_id)}")
    test_app.dependency_overrides.clear()
    
    # Then
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    # Verify standard set is deleted
    remaining_set = await mock_mongodb.standard_sets.find_one({"_id": set_result.inserted_id})
    assert remaining_set is None
    
    # Verify associated standards are deleted
    remaining_standards = await mock_mongodb.standards.find(
        {"standard_set_id": set_result.inserted_id}
    ).to_list(None)
    assert len(remaining_standards) == 0

@pytest.mark.asyncio
async def test_delete_standard_set_returns_404_when_not_found(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test deletion of non-existent standard set.
    
    Given: No standard set exists with the specified ID
    When: Attempting to delete the standard set
    Then: Should return 404 with not found message
    """
    # Given
    non_existent_id = str(ObjectId())

    # When
    repo = StandardSetRepository(mock_mongodb.standard_sets)
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    test_app.dependency_overrides[get_standard_set_repo] = lambda: repo
    response = test_client.delete(f"/api/v1/standard-sets/{non_existent_id}")
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 404
    data = response.json()
    assert "Standard set not found" in data["detail"]

@pytest.mark.asyncio
async def test_get_standard_set_by_id_handles_invalid_id_format(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test validation of ID format for get endpoint.
    
    Given: An invalid ID format
    When: Requesting a standard set with that ID
    Then: Should return 400 with validation error
    """
    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.get("/api/v1/standard-sets/invalid-id")

    # Then
    assert response.status_code == 400
    data = response.json()
    assert "Invalid ObjectId format" in data["detail"]

@pytest.mark.asyncio
async def test_delete_standard_set_handles_invalid_id_format(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test validation of ID format for delete endpoint.
    
    Given: An invalid ID format
    When: Attempting to delete a standard set with that ID
    Then: Should return 400 with validation error
    """
    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.delete("/api/v1/standard-sets/invalid-id")

    # Then
    assert response.status_code == 400
    data = response.json()
    assert "Invalid ObjectId format" in data["detail"] 