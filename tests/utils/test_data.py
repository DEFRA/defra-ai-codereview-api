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
def valid_standard_set_data():
    """Create valid standard set test data."""
    return {
        "name": "Test Standard Set",
        "description": "Test Description",
        "standards": [
            {
                "name": "Test Standard",
                "description": "Test Description"
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