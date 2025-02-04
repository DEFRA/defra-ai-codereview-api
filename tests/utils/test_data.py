"""Test data fixtures for use across tests."""
import pytest
from datetime import datetime, UTC
from bson import ObjectId

@pytest.fixture
def valid_classification_data():
    """Create valid classification test data."""
    return {
        "name": "Test Classification"
    }

@pytest.fixture
def valid_code_review_data():
    """Create valid code review test data."""
    return {
        "title": "Test Code Review",
        "description": "Test Description",
        "repository_url": "https://github.com/test/repo",
        "branch": "main",
        "pull_request_url": "https://github.com/test/repo/pull/1"
    }

@pytest.fixture
def standard_set_data():
    """Test data for standard set creation."""
    return {
        "name": "Test Standards",
        "repository_url": "https://github.com/org/test-standards",
        "custom_prompt": "Test prompt for standards analysis"
    }

@pytest.fixture
def standard_set_with_standards():
    """Test data for standard set with standards."""
    return {
        "_id": str(ObjectId()),
        "name": "Test Standards",
        "repository_url": "https://github.com/org/test-standards",
        "custom_prompt": "Test prompt for standards analysis",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "standards": [
            {
                "_id": str(ObjectId()),
                "title": "Test Standard 1",
                "description": "Test description 1",
                "category": "security",
                "severity": "high",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat()
            }
        ]
    }

def create_db_document(**kwargs) -> dict:
    """Create a database document with common fields.
    
    Args:
        **kwargs: Additional fields to add to the document
        
    Returns:
        dict: Document with _id and timestamps
    """
    return {
        "_id": ObjectId(),
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **kwargs
    } 