"""Integration tests for the complete code review processing flow.

This module contains integration tests that verify the end-to-end functionality of:
1. Processing repositories through git_repos_agent
2. Checking compliance through standards_agent
3. Database state transitions during processing
"""
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, AsyncMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from src.models.code_review import ReviewStatus
from src.api.v1.code_reviews import process_code_review


@pytest.mark.asyncio
async def test_process_code_review_end_to_end_success(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful end-to-end code review processing.
    
    Given: A code review in STARTED state
    When: Processing through both agents completes successfully
    Then: Review should be marked as COMPLETED with compliance report
    """
    # Given
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    review_id = str(result.inserted_id)
    
    # Mock the repository processing
    mock_codebase = Path("test_codebase.txt")
    mock_standards = [Path("test_standard.txt")]
    mock_compliance_report = {
        "status": "compliant",
        "details": {
            "passed_checks": ["check1", "check2"],
            "failed_checks": [],
            "warnings": []
        }
    }
    
    # When
    with patch('src.api.v1.code_reviews.process_repositories') as mock_process, \
         patch('src.api.v1.code_reviews.check_compliance') as mock_compliance:
        
        # Setup mocks
        mock_process.return_value = (mock_codebase, mock_standards)
        mock_compliance.return_value = mock_compliance_report
        
        # Process the review
        with patch('src.database.db', mock_mongodb):
            await process_code_review(review_id, test_review["repository_url"])
    
    # Then
    # Verify database state transitions
    updated_review = await mock_mongodb.code_reviews.find_one({"_id": result.inserted_id})
    assert updated_review["status"] == ReviewStatus.COMPLETED
    assert updated_review["compliance_report"] == mock_compliance_report
    assert "updated_at" in updated_review
    
    # Verify mock calls
    mock_process.assert_called_once_with(test_review["repository_url"])
    mock_compliance.assert_called_once_with(mock_codebase, mock_standards)


@pytest.mark.asyncio
async def test_process_code_review_git_agent_failure(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test handling of git repository agent failures.
    
    Given: A code review in STARTED state
    When: Repository processing fails
    Then: Review should be marked as FAILED
    """
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
        # Simulate git agent failure
        mock_process.side_effect = Exception("Failed to clone repository")
        
        with patch('src.database.db', mock_mongodb):
            await process_code_review(review_id, test_review["repository_url"])
    
    # Then
    updated_review = await mock_mongodb.code_reviews.find_one({"_id": result.inserted_id})
    assert updated_review["status"] == ReviewStatus.FAILED
    assert "updated_at" in updated_review
    
    # Verify mock calls
    mock_process.assert_called_once_with(test_review["repository_url"])


@pytest.mark.asyncio
async def test_process_code_review_standards_agent_failure(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test handling of standards agent failures.
    
    Given: A code review in STARTED state
    When: Standards compliance check fails
    Then: Review should be marked as FAILED
    """
    # Given
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    review_id = str(result.inserted_id)
    
    # Mock the repository processing
    mock_codebase = Path("test_codebase.txt")
    mock_standards = [Path("test_standard.txt")]
    
    # When
    with patch('src.api.v1.code_reviews.process_repositories') as mock_process, \
         patch('src.api.v1.code_reviews.check_compliance') as mock_compliance:
        
        # Setup mocks
        mock_process.return_value = (mock_codebase, mock_standards)
        mock_compliance.side_effect = Exception("Failed to check compliance")
        
        # Process the review
        with patch('src.database.db', mock_mongodb):
            await process_code_review(review_id, test_review["repository_url"])
    
    # Then
    updated_review = await mock_mongodb.code_reviews.find_one({"_id": result.inserted_id})
    assert updated_review["status"] == ReviewStatus.FAILED
    assert "updated_at" in updated_review
    
    # Verify mock calls
    mock_process.assert_called_once_with(test_review["repository_url"])
    mock_compliance.assert_called_once_with(mock_codebase, mock_standards)


@pytest.mark.asyncio
async def test_process_code_review_state_transitions(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test state transitions during code review processing.
    
    Given: A code review in STARTED state
    When: Processing through both agents
    Then: Should transition through expected states
    """
    # Given
    test_review = {
        "repository_url": "https://github.com/example/repo1",
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await mock_mongodb.code_reviews.insert_one(test_review)
    review_id = str(result.inserted_id)
    
    # Mock the repository processing
    mock_codebase = Path("test_codebase.txt")
    mock_standards = [Path("test_standard.txt")]
    mock_compliance_report = {"status": "compliant"}
    
    async def check_state(expected_status: ReviewStatus) -> None:
        current_review = await mock_mongodb.code_reviews.find_one({"_id": result.inserted_id})
        assert current_review["status"] == expected_status
    
    # When/Then
    with patch('src.api.v1.code_reviews.process_repositories') as mock_process, \
         patch('src.api.v1.code_reviews.check_compliance') as mock_compliance, \
         patch('src.database.db', mock_mongodb):
        
        # Setup mocks
        mock_process.return_value = (mock_codebase, mock_standards)
        mock_compliance.return_value = mock_compliance_report
        
        # Initial state
        await check_state(ReviewStatus.STARTED)
        
        # Process the review
        await process_code_review(review_id, test_review["repository_url"])
        
        # Final state
        await check_state(ReviewStatus.COMPLETED)
    
    # Verify mock calls
    mock_process.assert_called_once_with(test_review["repository_url"])
    mock_compliance.assert_called_once_with(mock_codebase, mock_standards) 