"""Integration tests for code reviews API endpoints.

Tests the functionality of:
1. get_classifications function
2. process_code_review function
3. Error handling in get_code_review
4. Standard set lookup in get_code_reviews
"""
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from src.models.code_review import ReviewStatus
from src.models.classification import Classification


@pytest.mark.asyncio
async def test_get_classifications(
    test_app: FastAPI,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test get_classifications function.
    
    Given: Multiple classifications exist in database
    When: Calling get_classifications
    Then: Should return list of Classification objects
    """
    # Given
    test_classifications = [
        {
            "_id": ObjectId(),
            "name": "Python",
            "description": "Python code"
        },
        {
            "_id": ObjectId(),
            "name": "JavaScript",
            "description": "JavaScript code"
        }
    ]
    await mock_mongodb.classifications.insert_many(test_classifications)

    # When
    from src.api.v1.code_reviews import get_classifications
    result = await get_classifications(mock_mongodb)

    # Then
    assert len(result) == 2
    assert all(isinstance(c, Classification) for c in result)
    assert result[0].name == "Python"
    assert result[1].name == "JavaScript"


@pytest.mark.asyncio
async def test_process_code_review_success(
    test_app: FastAPI,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test successful code review processing.
    
    Given: Valid review ID and repository URL
    When: Processing code review
    Then: Should update review status and add compliance reports
    """
    # Given
    review_id = str(ObjectId())
    repository_url = "https://github.com/example/repo"
    standard_sets = [str(ObjectId())]
    
    # Mock external functions
    async def mock_process_repositories(repo_url):
        mock_file = MagicMock()
        mock_file.parent = "/tmp/repo"
        return mock_file

    async def mock_analyze_classifications(path, classifications):
        return ["class1", "class2"]

    async def mock_check_compliance(codebase, standards, review_id, name):
        mock_file = MagicMock()
        mock_file.read_text.return_value = "Compliance report"
        return mock_file

    # Insert test data
    await mock_mongodb.code_reviews.insert_one({
        "_id": ObjectId(review_id),
        "repository_url": repository_url,
        "standard_sets": standard_sets,
        "status": ReviewStatus.STARTED
    })
    
    await mock_mongodb.standard_sets.insert_one({
        "_id": ObjectId(standard_sets[0]),
        "name": "Test Standards"
    })
    
    await mock_mongodb.standards.insert_one({
        "_id": ObjectId(),
        "standard_set_id": ObjectId(standard_sets[0]),
        "name": "Test Standard",
        "classification_ids": ["class1"]
    })

    # When
    with (
        patch('src.api.v1.code_reviews.process_repositories', mock_process_repositories),
        patch('src.api.v1.code_reviews.analyze_codebase_classifications', mock_analyze_classifications),
        patch('src.api.v1.code_reviews.check_compliance', mock_check_compliance)
    ):
        from src.api.v1.code_reviews import process_code_review
        await process_code_review(review_id, repository_url, standard_sets)

    # Then
    review = await mock_mongodb.code_reviews.find_one({"_id": ObjectId(review_id)})
    assert review["status"] == ReviewStatus.COMPLETED
    assert len(review["compliance_reports"]) == 1
    assert review["compliance_reports"][0]["standard_set_name"] == "Test Standards"
    assert review["compliance_reports"][0]["report"] == "Compliance report"


@pytest.mark.asyncio
async def test_process_code_review_failure(
    test_app: FastAPI,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test code review processing failure.
    
    Given: Valid review ID but processing fails
    When: Processing code review
    Then: Should update review status to FAILED
    """
    # Given
    review_id = str(ObjectId())
    repository_url = "https://github.com/example/repo"
    standard_sets = [str(ObjectId())]
    
    # Insert test data
    await mock_mongodb.code_reviews.insert_one({
        "_id": ObjectId(review_id),
        "repository_url": repository_url,
        "standard_sets": standard_sets,
        "status": ReviewStatus.STARTED
    })

    # Mock process_repositories to raise an exception
    async def mock_process_repositories(repo_url):
        raise Exception("Processing failed")

    # When
    with patch('src.api.v1.code_reviews.process_repositories', mock_process_repositories):
        from src.api.v1.code_reviews import process_code_review
        await process_code_review(review_id, repository_url, standard_sets)

    # Then
    review = await mock_mongodb.code_reviews.find_one({"_id": ObjectId(review_id)})
    assert review["status"] == ReviewStatus.FAILED


@pytest.mark.asyncio
async def test_process_code_review_standard_set_not_found(
    test_app: FastAPI,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test process_code_review when standard set is not found.
    
    Given: Valid review ID but standard set doesn't exist
    When: Processing code review
    Then: Should log warning and continue processing
    """
    # Given
    review_id = str(ObjectId())
    repository_url = "https://github.com/example/repo"
    standard_sets = [str(ObjectId())]
    
    # Insert test data
    await mock_mongodb.code_reviews.insert_one({
        "_id": ObjectId(review_id),
        "repository_url": repository_url,
        "standard_sets": standard_sets,
        "status": ReviewStatus.STARTED
    })

    # Mock external functions
    async def mock_process_repositories(repo_url):
        mock_file = MagicMock()
        mock_file.parent = "/tmp/repo"
        return mock_file

    async def mock_analyze_classifications(path, classifications):
        return ["class1", "class2"]

    # When
    with (
        patch('src.api.v1.code_reviews.process_repositories', mock_process_repositories),
        patch('src.api.v1.code_reviews.analyze_codebase_classifications', mock_analyze_classifications)
    ):
        from src.api.v1.code_reviews import process_code_review
        await process_code_review(review_id, repository_url, standard_sets)

    # Then
    review = await mock_mongodb.code_reviews.find_one({"_id": ObjectId(review_id)})
    assert review["status"] == ReviewStatus.COMPLETED
    assert len(review["compliance_reports"]) == 0


@pytest.mark.asyncio
async def test_process_code_review_no_matching_standards(
    test_app: FastAPI,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test process_code_review when no matching standards found.
    
    Given: Valid review ID but no standards match classifications
    When: Processing code review
    Then: Should log warning and continue processing
    """
    # Given
    review_id = str(ObjectId())
    repository_url = "https://github.com/example/repo"
    standard_sets = [str(ObjectId())]
    
    # Insert test data
    await mock_mongodb.code_reviews.insert_one({
        "_id": ObjectId(review_id),
        "repository_url": repository_url,
        "standard_sets": standard_sets,
        "status": ReviewStatus.STARTED
    })
    
    await mock_mongodb.standard_sets.insert_one({
        "_id": ObjectId(standard_sets[0]),
        "name": "Test Standards"
    })

    # Mock external functions
    async def mock_process_repositories(repo_url):
        mock_file = MagicMock()
        mock_file.parent = "/tmp/repo"
        return mock_file

    async def mock_analyze_classifications(path, classifications):
        return ["class1", "class2"]

    # When
    with (
        patch('src.api.v1.code_reviews.process_repositories', mock_process_repositories),
        patch('src.api.v1.code_reviews.analyze_codebase_classifications', mock_analyze_classifications)
    ):
        from src.api.v1.code_reviews import process_code_review
        await process_code_review(review_id, repository_url, standard_sets)

    # Then
    review = await mock_mongodb.code_reviews.find_one({"_id": ObjectId(review_id)})
    assert review["status"] == ReviewStatus.COMPLETED
    assert len(review["compliance_reports"]) == 0


@pytest.mark.asyncio
async def test_process_code_review_compliance_check_error(
    test_app: FastAPI,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test process_code_review when compliance check fails.
    
    Given: Valid review ID but compliance check raises error
    When: Processing code review
    Then: Should log error and continue processing
    """
    # Given
    review_id = str(ObjectId())
    repository_url = "https://github.com/example/repo"
    standard_sets = [str(ObjectId())]
    
    # Insert test data
    await mock_mongodb.code_reviews.insert_one({
        "_id": ObjectId(review_id),
        "repository_url": repository_url,
        "standard_sets": standard_sets,
        "status": ReviewStatus.STARTED
    })
    
    await mock_mongodb.standard_sets.insert_one({
        "_id": ObjectId(standard_sets[0]),
        "name": "Test Standards"
    })
    
    await mock_mongodb.standards.insert_one({
        "_id": ObjectId(),
        "standard_set_id": ObjectId(standard_sets[0]),
        "name": "Test Standard",
        "classification_ids": ["class1"]
    })

    # Mock external functions
    async def mock_process_repositories(repo_url):
        mock_file = MagicMock()
        mock_file.parent = "/tmp/repo"
        return mock_file

    async def mock_analyze_classifications(path, classifications):
        return ["class1", "class2"]

    async def mock_check_compliance(codebase, standards, review_id, name):
        raise Exception("Compliance check failed")

    # When
    with (
        patch('src.api.v1.code_reviews.process_repositories', mock_process_repositories),
        patch('src.api.v1.code_reviews.analyze_codebase_classifications', mock_analyze_classifications),
        patch('src.api.v1.code_reviews.check_compliance', mock_check_compliance)
    ):
        from src.api.v1.code_reviews import process_code_review
        await process_code_review(review_id, repository_url, standard_sets)

    # Then
    review = await mock_mongodb.code_reviews.find_one({"_id": ObjectId(review_id)})
    assert review["status"] == ReviewStatus.COMPLETED
    assert len(review["compliance_reports"]) == 0


@pytest.mark.asyncio
async def test_get_code_review_invalid_id(
    test_app: FastAPI,
    test_client: TestClient
) -> None:
    """
    Test get_code_review with invalid ID format.
    
    Given: Invalid ObjectId format
    When: Getting specific code review
    Then: Should return 400 error
    """
    # When
    response = test_client.get("/api/v1/code-reviews/invalid-id")

    # Then
    assert response.status_code == 400
    assert "Invalid review ID format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_code_review_database_error(
    test_app: FastAPI,
    test_client: TestClient
) -> None:
    """
    Test get_code_review with database error.
    
    Given: Valid ID but database error occurs
    When: Getting specific code review
    Then: Should return 500 error
    """
    # Given
    valid_id = str(ObjectId())
    
    # Mock database to raise exception
    async def mock_get_database():
        raise Exception("Database error")

    # When
    with patch('src.api.v1.code_reviews.get_database', mock_get_database):
        response = test_client.get(f"/api/v1/code-reviews/{valid_id}")

    # Then
    assert response.status_code == 500
    assert "Error fetching code review" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_code_review_standard_set_error(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test get_code_review when standard set lookup fails.
    
    Given: Valid review but standard set lookup fails
    When: Getting specific code review
    Then: Should handle error and return review with unknown standard set
    """
    # Given
    review_id = str(ObjectId())
    standard_set_id = str(ObjectId())
    
    await mock_mongodb.code_reviews.insert_one({
        "_id": ObjectId(review_id),
        "repository_url": "https://github.com/example/repo",
        "standard_sets": [standard_set_id],
        "status": ReviewStatus.COMPLETED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })

    # When
    response = test_client.get(f"/api/v1/code-reviews/{review_id}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["standard_sets"][0]["name"] == "Unknown Standard Set"


@pytest.mark.asyncio
async def test_get_code_reviews_standard_set_lookup(
    test_app: FastAPI,
    test_client: TestClient,
    mock_mongodb: AsyncMongoMockClient
) -> None:
    """
    Test standard set lookup in get_code_reviews.
    
    Given: Code review with standard sets exists
    When: Getting all code reviews
    Then: Should include standard set info in response
    """
    # Given
    standard_set_id = str(ObjectId())
    missing_set_id = str(ObjectId())
    
    await mock_mongodb.code_reviews.insert_one({
        "_id": ObjectId(),
        "repository_url": "https://github.com/example/repo",
        "standard_sets": [standard_set_id, missing_set_id],
        "status": ReviewStatus.COMPLETED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })
    
    await mock_mongodb.standard_sets.insert_one({
        "_id": ObjectId(standard_set_id),
        "name": "Test Standards"
    })

    # When
    response = test_client.get("/api/v1/code-reviews")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert len(data[0]["standard_sets"]) == 2
    assert data[0]["standard_sets"][0]["name"] == "Test Standards"
    assert data[0]["standard_sets"][1]["name"] == "Unknown Standard Set"
    assert data[0]["standard_sets"][1]["id"] == missing_set_id 