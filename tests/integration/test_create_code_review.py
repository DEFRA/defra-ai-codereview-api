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
from bson import ObjectId
import asyncio
from unittest.mock import MagicMock
from unittest.mock import AsyncMock
from src.api.v1.code_reviews import process_code_review, run_agent_process
from src.api.dependencies import get_database


@pytest.mark.asyncio
async def test_create_code_review_succeeds_with_valid_input(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful creation of a code review.
    
    Given: A valid repository URL and standard sets
    When: Creating a new code review
    Then: Response should be 201 with correct review data
    """
    # Given
    # Create test standard sets first
    security_set = {
        "name": "Security Standards",
        "repository_url": "https://github.com/org/security-standards",
        "custom_prompt": "Test security prompt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    performance_set = {
        "name": "Performance Standards",
        "repository_url": "https://github.com/org/performance-standards",
        "custom_prompt": "Test performance prompt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    security_result = await mock_mongodb.standard_sets.insert_one(security_set)
    performance_result = await mock_mongodb.standard_sets.insert_one(performance_set)
    
    test_review = {
        "repository_url": "https://github.com/example/new-repo",
        "standard_sets": [str(security_result.inserted_id), str(performance_result.inserted_id)]
    }

    # When
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    response = test_client.post("/api/v1/code-reviews", json=test_review)
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 201
    data = response.json()
    assert data["repository_url"] == test_review["repository_url"]
    assert len(data["standard_sets"]) == 2
    assert any(s["name"] == "Security Standards" for s in data["standard_sets"])
    assert any(s["name"] == "Performance Standards" for s in data["standard_sets"])
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
    
    Given: A request body missing required fields
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
    # Create test standard set first
    security_set = {
        "name": "Security Standards",
        "repository_url": "https://github.com/org/security-standards",
        "custom_prompt": "Test security prompt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    security_result = await mock_mongodb.standard_sets.insert_one(security_set)
    
    test_review = {
        "repository_url": "https://github.com/example/new-repo",
        "standard_sets": [str(security_result.inserted_id)],
        "extra_field": "should be ignored"
    }

    # When
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    response = test_client.post("/api/v1/code-reviews", json=test_review)
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 201
    data = response.json()
    assert "extra_field" not in data
    assert data["repository_url"] == test_review["repository_url"]
    assert len(data["standard_sets"]) == 1
    assert data["standard_sets"][0]["name"] == "Security Standards"


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
    # Given
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "standard_sets": ["security"],
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
            await process_code_review(review_id, test_review["repository_url"], test_review["standard_sets"])

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
            json={
                "repository_url": "https://github.com/example/repo",
                "standard_sets": ["security"]
            }
        )

    # Then
    assert response.status_code == 500
    assert "Error creating code review" in response.json()["detail"]


def test_run_agent_process_handles_errors():
    """
    Test error handling in run_agent_process.
    
    Given: A process that encounters an error
    When: Running the agent process
    Then: Should handle the error gracefully and log it
    """
    # Given
    review_id = str(ObjectId())
    repo_url = "https://github.com/example/repo"
    standard_sets = ["security"]

    # When/Then
    with patch('src.api.v1.code_reviews.process_code_review') as mock_process, \
         patch('src.api.v1.code_reviews.logger') as mock_logger, \
         patch('asyncio.new_event_loop') as mock_loop:
        
        # Setup mock event loop
        mock_loop.return_value = MagicMock()
        mock_process.side_effect = Exception("Test error")
        
        # Run the process
        run_agent_process(review_id, repo_url, standard_sets)
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        assert "Error in agent process" in mock_logger.error.call_args[0][0]


def test_run_agent_process_executes_successfully():
    """
    Test successful execution of run_agent_process.
    
    Given: Valid review ID and repository URL
    When: Running the agent process
    Then: Should process the code review without errors
    """
    # Given
    review_id = str(ObjectId())
    repo_url = "https://github.com/example/repo"
    standard_sets = ["security", "performance"]

    # When/Then
    with patch('src.api.v1.code_reviews.process_code_review', new_callable=AsyncMock) as mock_process, \
         patch('asyncio.run') as mock_run:
        
        # Run the process
        run_agent_process(review_id, repo_url, standard_sets)

        # Verify process_code_review was passed to asyncio.run
        mock_run.assert_called_once()
        # Get the coroutine that was passed to asyncio.run
        coro = mock_run.call_args[0][0]
        # Execute the coroutine
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        mock_run.side_effect = lambda x: loop.run_until_complete(x)
        # Run the coroutine
        mock_run(coro)
        # Clean up
        loop.close()
        # Verify it was a call to _run with correct args
        assert coro.cr_code.co_name == '_run'
        assert mock_process.call_args.args == (review_id, repo_url, standard_sets)