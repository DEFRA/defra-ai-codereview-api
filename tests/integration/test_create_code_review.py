"""Integration tests for the code review creation and processing endpoints.

This module contains integration tests that verify the functionality of:
1. Creating new code reviews
2. Processing code reviews in the background
3. Error handling for various scenarios
"""
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from src.models.code_review import ReviewStatus


@pytest.mark.asyncio
async def test_create_code_review_succeeds_with_valid_input(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful creation of a code review.
    
    Given: A valid repository URL
    When: Creating a new code review
    Then: Response should be 201 with correct review data
    """
    # Given
    test_review = {
        "repository_url": "https://github.com/example/new-repo"
    }

    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.post("/api/v1/code-reviews", json=test_review)

    # Then
    assert response.status_code == 201
    data = response.json()
    assert data["repository_url"] == test_review["repository_url"]
    assert "_id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["status"] == ReviewStatus.STARTED


def test_create_code_review_fails_with_missing_required_fields(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test validation of required fields.
    
    Given: A request body missing the repository_url
    When: Creating a new code review
    Then: Response should be 422 with validation error details
    """
    # Given
    test_review = {}

    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.post("/api/v1/code-reviews", json=test_review)

    # Then
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_create_code_review_ignores_extra_fields(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test handling of extra fields in request.
    
    Given: A valid request with additional unknown fields
    When: Creating a new code review
    Then: Response should be 201 and extra fields should be ignored
    """
    # Given
    test_review = {
        "repository_url": "https://github.com/example/new-repo",
        "extra_field": "should be ignored"
    }

    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.post("/api/v1/code-reviews", json=test_review)

    # Then
    assert response.status_code == 201
    data = response.json()
    assert "extra_field" not in data
    assert data["repository_url"] == test_review["repository_url"]


@pytest.mark.asyncio
async def test_process_code_review_handles_processing_errors(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test error handling during code review processing.
    
    Given: A code review in STARTED state
    When: Processing fails with an exception
    Then: Review should be marked as FAILED
    """
    from src.api.v1.code_reviews import process_code_review
    
    # Given
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    review_id = str(result.inserted_id)
    
    # When
    with patch('src.api.v1.code_reviews.process_repositories') as mock_process:
        mock_process.side_effect = Exception("Test error")
        with patch('src.database.db', mock_mongodb):
            await process_code_review(review_id, test_review["repository_url"])
    
    # Then
    updated_review = await mock_mongodb.code_reviews.find_one({"_id": result.inserted_id})
    assert updated_review["status"] == ReviewStatus.FAILED
    assert "updated_at" in updated_review


@pytest.mark.asyncio
async def test_create_code_review_handles_database_errors(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test error handling for database failures.
    
    Given: A database connection that fails
    When: Creating a new code review
    Then: Response should be 500 with appropriate error message
    """
    # Given
    async def mock_get_database():
        raise Exception("Database connection error")
    
    # When
    with patch('src.api.v1.code_reviews.get_database', mock_get_database):
        response = test_client.post(
            "/api/v1/code-reviews",
            json={"repository_url": "https://github.com/example/repo"}
        )
    
    # Then
    assert response.status_code == 500
    assert "Error creating code review" in response.json()["detail"]


@pytest.mark.asyncio
async def test_process_code_review_completes_successfully(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful code review processing flow.
    
    Given: A code review in STARTED state
    When: Processing completes successfully
    Then: Review should be marked as COMPLETED with compliance report
    """
    from src.api.v1.code_reviews import process_code_review
    from pathlib import Path
    
    # Given
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    review_id = str(result.inserted_id)
    
    # When
    with patch('src.api.v1.code_reviews.process_repositories') as mock_process, \
         patch('src.api.v1.code_reviews.check_compliance') as mock_compliance:
        mock_process.return_value = (Path("codebase.txt"), [Path("standards.txt")])
        mock_compliance.return_value = {"status": "compliant"}
        
        with patch('src.database.db', mock_mongodb):
            await process_code_review(review_id, test_review["repository_url"])
    
    # Then
    updated_review = await mock_mongodb.code_reviews.find_one({"_id": result.inserted_id})
    assert updated_review["status"] == ReviewStatus.COMPLETED
    assert updated_review["compliance_report"] == {"status": "compliant"}
    assert "updated_at" in updated_review


@pytest.mark.asyncio
async def test_process_code_review_handles_compliance_check_errors(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test error handling during compliance check.
    
    Given: A code review in STARTED state
    When: Compliance check fails
    Then: Review should be marked as FAILED
    """
    from src.api.v1.code_reviews import process_code_review
    from pathlib import Path
    
    # Given
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    review_id = str(result.inserted_id)
    
    # When
    with patch('src.api.v1.code_reviews.process_repositories') as mock_process, \
         patch('src.api.v1.code_reviews.check_compliance') as mock_compliance:
        mock_process.return_value = (Path("codebase.txt"), [Path("standards.txt")])
        mock_compliance.side_effect = Exception("Compliance check failed")
        
        with patch('src.database.db', mock_mongodb):
            await process_code_review(review_id, test_review["repository_url"])
    
    # Then
    updated_review = await mock_mongodb.code_reviews.find_one({"_id": result.inserted_id})
    assert updated_review["status"] == ReviewStatus.FAILED
    assert "updated_at" in updated_review 