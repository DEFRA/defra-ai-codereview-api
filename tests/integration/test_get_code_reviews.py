"""Integration tests for the code reviews listing endpoint.

This module contains integration tests that verify the functionality of:
1. Retrieving all code reviews
2. Handling invalid data in the database
3. Error handling for database failures
"""
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from src.models.code_review import ReviewStatus


@pytest.mark.asyncio
async def test_get_code_reviews_returns_all_reviews(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful retrieval of all code reviews.
    
    Given: Multiple code reviews exist in the database
    When: Requesting all code reviews
    Then: Should return 200 with list of all reviews
    """
    # Given
    test_reviews = [
        {
            "repository_url": "https://github.com/example/repo1",
            "status": ReviewStatus.COMPLETED,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "repository_url": "https://github.com/example/repo2",
            "status": ReviewStatus.STARTED,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]
    await mock_mongodb.code_reviews.insert_many(test_reviews)

    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.get("/api/v1/code-reviews")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["repository_url"] == test_reviews[0]["repository_url"]
    assert data[1]["repository_url"] == test_reviews[1]["repository_url"]


@pytest.mark.asyncio
async def test_get_code_reviews_filters_invalid_records(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test handling of invalid records in database.
    
    Given: A code review with invalid _id exists in database
    When: Requesting all code reviews
    Then: Should return 200 with invalid records filtered out
    """
    # Given
    test_reviews = [
        {
            "_id": "",  # Invalid _id
            "repository_url": "https://github.com/example/repo1",
            "status": ReviewStatus.COMPLETED,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]
    await mock_mongodb.code_reviews.insert_many(test_reviews)

    # When
    with patch('src.database.db', mock_mongodb):
        response = test_client.get("/api/v1/code-reviews")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Invalid review should be filtered out


def test_get_code_reviews_handles_database_errors(
    test_app: FastAPI,
    test_client: TestClient
) -> None:
    """
    Test error handling for database failures.
    
    Given: Database connection fails
    When: Requesting all code reviews
    Then: Should return 500 with error details
    """
    # Given
    async def mock_get_database():
        raise Exception("Database error")

    # When
    with patch('src.api.v1.code_reviews.get_database', mock_get_database):
        response = test_client.get("/api/v1/code-reviews")

    # Then
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data 