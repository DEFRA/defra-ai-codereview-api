"""Integration tests for the code review API endpoints.

This module contains integration tests that verify the functionality of the code review
REST API endpoints, focusing on:
1. Creating new code reviews
2. Retrieving code reviews
3. Error handling
4. Input validation
"""
from datetime import datetime, timezone
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from bson import ObjectId
from src.models.code_review import ReviewStatus, CodeReviewCreate
from src.models.standard_set import StandardSet
from src.api.dependencies import get_database, get_code_review_repo, get_standard_set_repo
from src.repositories.code_review_repo import CodeReviewRepository
from src.repositories.standard_set_repo import StandardSetRepository


@pytest.mark.asyncio
async def test_create_code_review_success(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful creation of a code review via API.

    Given: Valid repository URL and standard sets
    When: POST request to /code-reviews
    Then: Response should be 201 with correct review data
    """
    # Given
    # Create test standard sets first
    standard_set_repo = StandardSetRepository(mock_mongodb.standard_sets)
    standard_set = StandardSet(
        name="Security Standards",
        repository_url="https://github.com/org/security-standards",
        custom_prompt="Test security prompt"
    )
    created_set = await standard_set_repo.create(standard_set)

    test_review = {
        "repository_url": "https://github.com/example/new-repo",
        "standard_sets": [str(created_set.id)]
    }

    # When
    response = test_client.post("/api/v1/code-reviews", json=test_review)

    # Then
    assert response.status_code == 201
    data = response.json()
    assert data["repository_url"] == test_review["repository_url"]
    assert len(data["standard_sets"]) == 1
    assert data["standard_sets"][0]["name"] == "Security Standards"
    assert "_id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["status"] == ReviewStatus.STARTED


@pytest.mark.asyncio
async def test_get_code_reviews_success(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful retrieval of all code reviews.

    Given: Multiple code reviews in the database
    When: GET request to /code-reviews
    Then: Response should be 200 with list of reviews
    """
    # Given
    # Create test standard sets first
    standard_set_repo = StandardSetRepository(mock_mongodb.standard_sets)
    standard_set = StandardSet(
        name="Security Standards",
        repository_url="https://github.com/org/security-standards",
        custom_prompt="Test security prompt"
    )
    created_set = await standard_set_repo.create(standard_set)

    # Create test reviews
    code_review_repo = CodeReviewRepository(mock_mongodb.code_reviews)
    for i in range(3):
        review = CodeReviewCreate(
            repository_url=f"https://github.com/example/repo{i}",
            standard_sets=[str(created_set.id)]
        )
        await code_review_repo.create(review)

    # When
    response = test_client.get("/api/v1/code-reviews")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    for review in data:
        assert "_id" in review
        assert "repository_url" in review
        assert "status" in review
        assert review["status"] == ReviewStatus.STARTED


@pytest.mark.asyncio
async def test_get_code_review_by_id_success(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful retrieval of a specific code review.

    Given: A code review in the database
    When: GET request to /code-reviews/{id}
    Then: Response should be 200 with review data
    """
    # Given
    # Create test standard set
    standard_set_repo = StandardSetRepository(mock_mongodb.standard_sets)
    standard_set = StandardSet(
        name="Security Standards",
        repository_url="https://github.com/org/security-standards",
        custom_prompt="Test security prompt"
    )
    created_set = await standard_set_repo.create(standard_set)

    # Create test review
    code_review_repo = CodeReviewRepository(mock_mongodb.code_reviews)
    review = CodeReviewCreate(
        repository_url="https://github.com/example/repo",
        standard_sets=[str(created_set.id)]
    )
    created_review = await code_review_repo.create(review)

    # When
    response = test_client.get(
        f"/api/v1/code-reviews/{str(created_review.id)}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["_id"] == str(created_review.id)
    assert data["repository_url"] == review.repository_url
    assert data["status"] == ReviewStatus.STARTED
    assert len(data["standard_sets"]) == 1
    assert data["standard_sets"][0]["name"] == "Security Standards"


@pytest.mark.asyncio
async def test_get_code_review_not_found(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test 404 response when code review doesn't exist.

    Given: A non-existent review ID
    When: GET request to /code-reviews/{id}
    Then: Response should be 404
    """
    # Given
    non_existent_id = str(ObjectId())

    # When
    response = test_client.get(f"/api/v1/code-reviews/{non_existent_id}")

    # Then
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert non_existent_id in data["detail"]


@pytest.mark.asyncio
async def test_get_code_review_invalid_id(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test 400 response when review ID is invalid.

    Given: An invalid review ID format
    When: GET request to /code-reviews/{id}
    Then: Response should be 400
    """
    # Given
    invalid_id = "not-a-valid-id"

    # When
    response = test_client.get(f"/api/v1/code-reviews/{invalid_id}")

    # Then
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Invalid review ID format" in data["detail"]
