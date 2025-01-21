"""Integration tests for code review processing."""
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, AsyncMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from src.models.code_review import ReviewStatus


@pytest.mark.asyncio
async def test_create_code_review_success(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient,
    tmp_path: Path
) -> None:
    """Test successful code review creation."""
    # Given
    # Create a test standard set
    standard_set = {
        "name": "Test Standard Set",
        "description": "Test Description"
    }
    standard_set_result = await mock_mongodb.standard_sets.insert_one(standard_set)
    standard_set_id = str(standard_set_result.inserted_id)
    
    # Create mock files
    mock_codebase = tmp_path / "test_codebase.txt"
    mock_codebase.write_text("Mock codebase content")
    
    # When
    with patch('src.agents.git_repos_agent.process_repositories', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_codebase
        
        # Make the API request
        response = test_client.post(
            "/api/v1/code-reviews",
            json={
                "repository_url": "https://github.com/example/repo1",
                "standard_sets": [standard_set_id]
            }
        )
    
    # Then
    assert response.status_code == 201
    data = response.json()
    assert data["repository_url"] == "https://github.com/example/repo1"
    assert data["status"] == ReviewStatus.STARTED
    assert len(data["standard_sets"]) == 1
    assert data["standard_sets"][0]["id"] == standard_set_id


@pytest.mark.asyncio
async def test_create_code_review_invalid_standard_set(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test code review creation with invalid standard set."""
    # When
    response = test_client.post(
        "/api/v1/code-reviews",
        json={
            "repository_url": "https://github.com/example/repo1",
            "standard_sets": ["invalid_id"]
        }
    )
    
    # Then
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_create_code_review_missing_fields(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test code review creation with missing required fields."""
    # When - Missing repository_url
    response = test_client.post(
        "/api/v1/code-reviews",
        json={
            "standard_sets": ["some_id"]
        }
    )
    
    # Then
    assert response.status_code == 422

    # When - Missing standard_sets
    response = test_client.post(
        "/api/v1/code-reviews",
        json={
            "repository_url": "https://github.com/example/repo1"
        }
    )
    
    # Then
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_code_review_status(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test retrieving a code review's status."""
    # Given
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "standard_sets": [],
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    review_id = str(result.inserted_id)
    
    # When
    response = test_client.get(f"/api/v1/code-reviews/{review_id}")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ReviewStatus.STARTED
    assert data["repository_url"] == test_review["repository_url"]