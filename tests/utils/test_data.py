"""Test data fixtures for use across tests."""
import pytest
from datetime import datetime, UTC
from bson import ObjectId

def create_classification_test_data(name: str = "Test Classification") -> dict:
    """Create a classification test document with default values.
    
    Args:
        name: Optional name for the classification. Defaults to "Test Classification"
        
    Returns:
        dict: Classification document with default test values
    """
    return create_db_document(
        name=name
    )

def create_standard_set_test_data(set_id: ObjectId = None) -> dict:
    """Create a standard set test document with default values.
    
    Args:
        set_id: Optional ObjectId for the standard set. If not provided, a new one is created.
        
    Returns:
        dict: Standard set document with default test values
    """
    return create_db_document(
        _id=set_id or ObjectId(),
        name="Test Standard Set",
        repository_url="https://github.com/test/repo",
        custom_prompt="Test prompt"
    )

def create_standard_set_reference(set_id: str = None) -> dict:
    """Create a standard set reference document for code reviews.
    
    Args:
        set_id: Optional string ID for the standard set. If not provided, a new one is created.
        
    Returns:
        dict: Standard set reference with ID and name
    """
    return {
        "_id": set_id or str(ObjectId()),
        "name": "Test Standard Set"
    }

def create_standard_test_data(set_id: ObjectId, index: int = 0) -> dict:
    """Create a standard test document with default values.
    
    Args:
        set_id: ObjectId of the parent standard set
        index: Optional index to create unique standards
        
    Returns:
        dict: Standard document with default test values
    """
    return create_db_document(
        text=f"Standard {index}",
        repository_path=f"/path/to/standard_{index}",
        standard_set_id=set_id,
        classification_ids=[ObjectId(), ObjectId()]
    )

def create_db_document(**kwargs) -> dict:
    """Create a database document with common fields.
    
    Args:
        **kwargs: Additional fields to add to the document
        
    Returns:
        dict: Document with _id and timestamps
    """
    return {
        "_id": kwargs.pop("_id", ObjectId()),
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **kwargs
    }

@pytest.fixture
def valid_classification_data():
    """Create valid classification test data for input validation."""
    return {
        "name": "Test Classification"
    }

@pytest.fixture
def valid_standard_set_data():
    """Create valid standard set test data for input validation."""
    return {
        "name": "Test Standard Set",
        "repository_url": "https://github.com/test/repo",
        "custom_prompt": "Test prompt"
    }

@pytest.fixture
def invalid_standard_set_data():
    """Create invalid standard set test data for input validation."""
    return {
        "name": "Test Standard Set"
        # Missing repository_url and custom_prompt
    }

@pytest.fixture
def valid_code_review_data():
    """Create valid code review test data for input validation."""
    standard_set_id = str(ObjectId())
    return {
        "repository_url": "https://github.com/test/repo",
        "standard_sets": [standard_set_id]
    }

@pytest.fixture
def invalid_code_review_data():
    """Create invalid code review test data for input validation."""
    return {
        "repository_url": "",  # Invalid empty URL
        "standard_sets": ["invalid-id"]  # Invalid ObjectId format
    }

def create_code_review_test_data(
    repository_url: str = "https://github.com/test/repo",
    standard_sets: list = None
) -> dict:
    """Create a test code review document with default values.
    
    Args:
        repository_url: Repository URL for the code review
        standard_sets: List of standard sets. If None, creates a default one
        
    Returns:
        dict: Code review document with test values
    """
    if standard_sets is None:
        standard_sets = [{
            "_id": str(ObjectId()),
            "name": "Test Standard Set"
        }]
    else:
        # Ensure _id is converted to string for response format
        standard_sets = [{
            "_id": str(set_data["_id"]) if isinstance(set_data["_id"], ObjectId) else set_data["_id"],
            "name": set_data["name"]
        } for set_data in standard_sets]
    
    return create_db_document(
        repository_url=repository_url,
        status="started",
        standard_sets=standard_sets,
        compliance_reports=[]
    )

def create_code_review_list_test_data(
    repository_url: str = "https://github.com/test/repo",
    standard_sets: list = None
) -> dict:
    """Create a test code review list document with default values."""
    if standard_sets is None:
        standard_sets = [{
            "_id": ObjectId(),
            "name": "Test Standard Set"
        }]
    
    return create_db_document(
        repository_url=repository_url,
        status="started",
        standard_sets=standard_sets
    ) 