"""Integration tests for get all code reviews endpoint."""
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from src.models.code_review import ReviewStatus


@pytest.mark.asyncio
async def test_get_code_reviews(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test getting all code reviews."""
    # Test data
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

    # Insert test data
    await mock_mongodb.code_reviews.insert_many(test_reviews)

    # Patch the database connection
    with patch('src.database.db', mock_mongodb):
        # Make request to get all code reviews
        response = test_client.get("/api/v1/code-reviews")

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["repository_url"] == test_reviews[0]["repository_url"]
    assert data[1]["repository_url"] == test_reviews[1]["repository_url"]


@pytest.mark.asyncio
async def test_get_code_reviews_with_invalid_id(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """Test get_code_reviews with invalid _id in database."""
    # Setup test data with invalid _id
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

    with patch('src.database.db', mock_mongodb):
        response = test_client.get("/api/v1/code-reviews")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Invalid review should be filtered out


def test_get_code_reviews_error(
    test_app: FastAPI,
    test_client: TestClient
) -> None:
    """Test error handling in get_code_reviews endpoint."""

    # Mock the database connection to raise an exception
    async def mock_get_database():
        raise Exception("Database error")

    with patch('src.api.v1.code_reviews.get_database', mock_get_database):
        response = test_client.get("/api/v1/code-reviews")

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data 