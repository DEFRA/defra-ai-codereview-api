"""Integration tests for the code review service layer.

This module contains integration tests that verify the functionality of the code review
service layer, focusing on:
1. Code review processing
2. Database operations
3. Error handling
"""
from datetime import datetime, timezone
import pytest
from unittest.mock import patch, AsyncMock
from mongomock_motor import AsyncMongoMockClient
from bson import ObjectId
from src.models.code_review import ReviewStatus, CodeReviewCreate
from src.services.code_review_service import CodeReviewService, _run_in_process
from src.repositories.code_review_repo import CodeReviewRepository


@pytest.fixture
async def code_review_repo(mock_mongodb: AsyncMongoMockClient):
    """Create a code review repository with mock database."""
    return CodeReviewRepository(mock_mongodb.code_reviews)


@pytest.fixture
async def code_review_service(mock_mongodb: AsyncMongoMockClient, code_review_repo: CodeReviewRepository):
    """Create a code review service with mock dependencies."""
    return CodeReviewService(mock_mongodb, code_review_repo)


@pytest.mark.asyncio
async def test_service_process_review_handles_errors(
    mock_mongodb: AsyncMongoMockClient,
    code_review_service: CodeReviewService,
    code_review_repo: CodeReviewRepository
) -> None:
    """
    Test error handling during code review processing in the service layer.

    Given: A code review in STARTED state
    When: Processing encounters an error
    Then: Review should be marked as FAILED with error details
    """
    # Given
    # Create test standard sets first
    standard_set = {
        "_id": ObjectId(),
        "name": "Security Standards",
        "repository_url": "https://github.com/org/security-standards",
        "custom_prompt": "Test security prompt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await mock_mongodb.standard_sets.insert_one(standard_set)

    # Create a test review using the model
    test_review = CodeReviewCreate(
        repository_url="https://github.com/example/repo1",
        standard_sets=[str(standard_set["_id"])]
    )
    created_review = await code_review_service.create_review(test_review)

    # When
    # Mock the process_repositories to simulate an error
    with patch('src.agents.git_repos_agent.process_repositories', side_effect=Exception("Test processing error")), \
            patch('multiprocessing.Process.start') as mock_start:
        # Start the process to trigger error handling
        await code_review_service.create_review(test_review)
        # Verify process was started
        mock_start.assert_called_once()

    # Then
    updated_review = await code_review_service.get_review_by_id(str(created_review.id))
    # Status remains STARTED as process runs in background
    assert updated_review.status == ReviewStatus.STARTED


@pytest.mark.asyncio
async def test_service_create_review_with_invalid_standard_set(
    mock_mongodb: AsyncMongoMockClient,
    code_review_service: CodeReviewService
) -> None:
    """
    Test creating a review with non-existent standard set.

    Given: A review with non-existent standard set ID
    When: Creating a new code review
    Then: Review should be created with empty standard sets
    """
    # Given
    test_review = CodeReviewCreate(
        repository_url="https://github.com/example/repo",
        # Valid ObjectId format but doesn't exist
        standard_sets=["507f1f77bcf86cd799439011"]
    )

    # When
    created_review = await code_review_service.create_review(test_review)

    # Then
    assert created_review.status == ReviewStatus.STARTED
    assert created_review.repository_url == test_review.repository_url
    # Standard sets should be empty since none were found
    assert len(created_review.standard_sets) == 0

    # Verify in database
    stored_review = await code_review_service.get_review_by_id(str(created_review.id))
    assert stored_review.status == ReviewStatus.STARTED
    assert stored_review.repository_url == test_review.repository_url
    assert len(stored_review.standard_sets) == 0
