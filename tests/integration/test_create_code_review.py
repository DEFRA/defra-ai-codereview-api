"""Integration tests for create code review endpoint."""
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from src.models.code_review import ReviewStatus


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


@pytest.mark.asyncio
async def test_process_code_review_error_handling(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test error handling in process_code_review background task."""
    from src.api.v1.code_reviews import process_code_review
    
    # Create a test review
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    review_id = str(result.inserted_id)
    
    # Mock process_repositories to raise an exception
    with patch('src.api.v1.code_reviews.process_repositories') as mock_process:
        mock_process.side_effect = Exception("Test error")
        
        # Run the background task
        with patch('src.database.db', mock_mongodb):
            await process_code_review(review_id, test_review["repository_url"])
    
    # Verify the review was updated with failed status
    updated_review = await mock_mongodb.code_reviews.find_one({"_id": result.inserted_id})
    assert updated_review["status"] == ReviewStatus.FAILED
    assert "updated_at" in updated_review


@pytest.mark.asyncio
async def test_create_code_review_database_error(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test error handling in create_code_review when database operation fails."""
    # Mock the database to raise an exception
    async def mock_get_database():
        raise Exception("Database connection error")
    
    with patch('src.api.v1.code_reviews.get_database', mock_get_database):
        response = test_client.post(
            "/api/v1/code-reviews",
            json={"repository_url": "https://github.com/example/repo"}
        )
    
    assert response.status_code == 500
    assert "Error creating code review" in response.json()["detail"]


@pytest.mark.asyncio
async def test_process_code_review_success(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test successful execution of process_code_review background task."""
    from src.api.v1.code_reviews import process_code_review
    from pathlib import Path
    
    # Create a test review
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    review_id = str(result.inserted_id)
    
    # Mock successful repository processing and compliance check
    with patch('src.api.v1.code_reviews.process_repositories') as mock_process, \
         patch('src.api.v1.code_reviews.check_compliance') as mock_compliance:
        
        mock_process.return_value = (Path("codebase.txt"), [Path("standards.txt")])
        mock_compliance.return_value = {"status": "compliant"}
        
        # Run the background task
        with patch('src.database.db', mock_mongodb):
            await process_code_review(review_id, test_review["repository_url"])
    
    # Verify the review was updated with completed status and compliance report
    updated_review = await mock_mongodb.code_reviews.find_one({"_id": result.inserted_id})
    assert updated_review["status"] == ReviewStatus.COMPLETED
    assert updated_review["compliance_report"] == {"status": "compliant"}
    assert "updated_at" in updated_review


@pytest.mark.asyncio
async def test_process_code_review_compliance_error(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test error handling in process_code_review when compliance check fails."""
    from src.api.v1.code_reviews import process_code_review
    from pathlib import Path
    
    # Create a test review
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    review_id = str(result.inserted_id)
    
    # Mock successful repository processing but failed compliance check
    with patch('src.api.v1.code_reviews.process_repositories') as mock_process, \
         patch('src.api.v1.code_reviews.check_compliance') as mock_compliance:
        
        mock_process.return_value = (Path("codebase.txt"), [Path("standards.txt")])
        mock_compliance.side_effect = Exception("Compliance check failed")
        
        # Run the background task
        with patch('src.database.db', mock_mongodb):
            await process_code_review(review_id, test_review["repository_url"])
    
    # Verify the review was updated with failed status
    updated_review = await mock_mongodb.code_reviews.find_one({"_id": result.inserted_id})
    assert updated_review["status"] == ReviewStatus.FAILED
    assert "updated_at" in updated_review 