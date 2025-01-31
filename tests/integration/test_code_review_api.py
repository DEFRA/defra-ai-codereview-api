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
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from bson import ObjectId
from src.models.code_review import ReviewStatus, CodeReviewCreate, CodeReview
from src.models.standard_set import StandardSet
from src.api.dependencies import get_database, get_code_review_service
from src.repositories.code_review_repo import CodeReviewRepository
from src.repositories.standard_set_repo import StandardSetRepository
from src.services.code_review_service import CodeReviewService, _run_in_process


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
        "_id": ObjectId(),
        "name": "Security Standards",
        "repository_url": "https://github.com/org/security-standards",
        "custom_prompt": "Test security prompt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    performance_set = {
        "_id": ObjectId(),
        "name": "Performance Standards",
        "repository_url": "https://github.com/org/performance-standards",
        "custom_prompt": "Test performance prompt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    await mock_mongodb.standard_sets.insert_one(security_set)
    await mock_mongodb.standard_sets.insert_one(performance_set)

    test_review = {
        "repository_url": "https://github.com/example/new-repo",
        "standard_sets": [str(security_set["_id"]), str(performance_set["_id"])]
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
    assert data["status"] == ReviewStatus.STARTED
    assert "_id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert isinstance(data["_id"], str)
    assert ObjectId.is_valid(data["_id"])

    # Verify database state
    review_doc = await mock_mongodb.code_reviews.find_one({"_id": ObjectId(data["_id"])})
    assert review_doc is not None
    assert review_doc["repository_url"] == test_review["repository_url"]
    assert len(review_doc["standard_sets"]) == 2
    assert review_doc["status"] == ReviewStatus.STARTED


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
    standard_set = {
        "_id": ObjectId(),
        "name": "Security Standards",
        "repository_url": "https://github.com/org/security-standards",
        "custom_prompt": "Test security prompt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await mock_mongodb.standard_sets.insert_one(standard_set)

    # Create test reviews
    for i in range(3):
        review = {
            "_id": ObjectId(),
            "repository_url": f"https://github.com/example/repo{i}",
            "standard_sets": [{
                "_id": standard_set["_id"],
                "name": standard_set["name"]
            }],
            "status": "started",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        await mock_mongodb.code_reviews.insert_one(review)

    # When
    test_app.dependency_overrides[get_database] = lambda: mock_mongodb
    response = test_client.get("/api/v1/code-reviews")
    test_app.dependency_overrides.clear()

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    for review in data:
        assert "_id" in review
        assert "repository_url" in review
        assert "status" in review
        assert "standard_sets" in review
        assert len(review["standard_sets"]) == 1
        assert review["standard_sets"][0]["name"] == "Security Standards"
        assert "created_at" in review
        assert "updated_at" in review


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
    test_cases = [
        # Missing repository_url
        {
            "input": {"standard_sets": ["123"]},
            "expected_field": "repository_url"
        },
        # Missing standard_sets
        {
            "input": {"repository_url": "https://github.com/example/repo"},
            "expected_field": "standard_sets"
        },
        # Empty standard_sets
        {
            "input": {
                "repository_url": "https://github.com/example/repo",
                "standard_sets": []
            },
            "expected_field": "standard_sets"
        },
        # Empty object
        {
            "input": {},
            "expected_fields": ["repository_url", "standard_sets"]
        }
    ]

    test_app.dependency_overrides[get_database] = lambda: mock_mongodb

    for test_case in test_cases:
        response = test_client.post(
            "/api/v1/code-reviews", json=test_case["input"])
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

        if "expected_fields" in test_case:
            # Multiple fields missing
            for field in test_case["expected_fields"]:
                assert any(err["loc"][1] == field for err in data["detail"])
        else:
            # Single field missing
            assert any(err["loc"][1] == test_case["expected_field"]
                       for err in data["detail"])

    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_code_review_starts_background_process(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test that code review creation starts background process.

    Given: A valid code review request
    When: Creating a new code review
    Then: Background process should be started with correct parameters
    """
    # Given
    security_set = {
        "_id": ObjectId(),
        "name": "Security Standards",
        "repository_url": "https://github.com/org/security-standards",
        "custom_prompt": "Test security prompt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await mock_mongodb.standard_sets.insert_one(security_set)

    test_review = {
        "repository_url": "https://github.com/example/new-repo",
        "standard_sets": [str(security_set["_id"])]
    }

    # Create a real repository with mock DB
    repo = CodeReviewRepository(mock_mongodb.code_reviews)

    # Create a mock service that will track process creation
    mock_service = AsyncMock(spec=CodeReviewService)

    # Setup the create method to use real repo but track process creation
    async def mock_create_review(review_create: CodeReviewCreate) -> CodeReview:
        created_review = await repo.create(review_create)
        return created_review

    mock_service.create_review.side_effect = mock_create_review

    # When
    with patch('src.api.dependencies.get_code_review_service', return_value=mock_service), \
            patch('multiprocessing.Process') as mock_process:

        test_app.dependency_overrides[get_database] = lambda: mock_mongodb
        response = test_client.post("/api/v1/code-reviews", json=test_review)
        test_app.dependency_overrides.clear()

        # Then
        assert response.status_code == 201
        data = response.json()

        # Verify review was created
        assert data["repository_url"] == test_review["repository_url"]
        assert len(data["standard_sets"]) == 1
        assert data["status"] == ReviewStatus.STARTED

        # Verify process creation
        mock_process.assert_called_once()
        process_args = mock_process.call_args[1]
        assert "target" in process_args
        assert "args" in process_args

        # Verify process arguments
        args = process_args["args"]
        assert len(args) == 3
        assert args[0] == data["_id"]  # review_id
        assert args[1] == test_review["repository_url"]
        assert args[2] == test_review["standard_sets"]

        # Verify process was started
        mock_process.return_value.start.assert_called_once()

        # Verify database state
        review_doc = await mock_mongodb.code_reviews.find_one({"_id": ObjectId(data["_id"])})
        assert review_doc is not None
        assert review_doc["repository_url"] == test_review["repository_url"]
        assert review_doc["status"] == ReviewStatus.STARTED


@pytest.mark.asyncio
async def test_run_in_process_handles_errors(
    mock_mongodb: AsyncMongoMockClient,
    caplog
) -> None:
    """
    Test error handling in the background process.

    Given: A process that encounters an error
    When: Running the background process
    Then: Should handle the error gracefully and update review status
    """
    # Given
    review_id = str(ObjectId())
    repo_url = "https://github.com/example/repo"
    standard_sets = ["security"]

    # Create the review in DB first
    review = {
        "_id": ObjectId(review_id),
        "repository_url": repo_url,
        "standard_sets": standard_sets,
        "status": ReviewStatus.STARTED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await mock_mongodb.code_reviews.insert_one(review)

    # When
    with patch('src.services.code_review_service.process_repositories') as mock_process:
        mock_process.side_effect = Exception("Test error")
        await _run_in_process(review_id, repo_url, standard_sets)

    # Then
    updated_review = await mock_mongodb.code_reviews.find_one({"_id": ObjectId(review_id)})
    assert updated_review is not None
    assert updated_review["status"] == ReviewStatus.FAILED
