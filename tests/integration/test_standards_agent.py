"""Integration tests for the standards agent."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call, PropertyMock
from bson import ObjectId
from datetime import datetime, UTC
from pathlib import Path
import tempfile
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.models.standard_set import StandardSet, StandardSetCreate
from src.models.classification import Classification
from src.repositories.standard_set_repo import StandardSetRepository
from src.services.standard_set_service import StandardSetService
from src.agents.standards_agent import process_standard_set
from src.database.database_utils import get_database

# Test Data Constants
TEST_REPO_URL = "https://github.com/test/standards-repo"
TEST_PROMPT = "Test prompt for standards analysis"


def create_standard_set_test_data(set_id: ObjectId = None) -> dict:
    """Create a standard set test document with consistent structure."""
    return {
        "_id": set_id or ObjectId(),
        "name": "Test Standard Set",
        "repository_url": TEST_REPO_URL,
        "custom_prompt": TEST_PROMPT,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }


def create_classification_test_data() -> list[dict]:
    """Create a set of test classifications with consistent structure."""
    return [
        {
            "_id": ObjectId(),
            "name": "Python",
            "description": "Python specific standards",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        },
        {
            "_id": ObjectId(),
            "name": "Security",
            "description": "Security standards",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        },
        {
            "_id": ObjectId(),
            "name": "Performance",
            "description": "Performance standards",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
    ]


def create_standard_test_data(standard_set_id: ObjectId, classification_ids: list[ObjectId] = None) -> dict:
    """Create a standard test document with consistent structure."""
    return {
        "_id": ObjectId(),
        "standard_set_id": standard_set_id,
        "title": "Test Standard",
        "content": "This is a test standard",
        "classification_ids": classification_ids or [],
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }


@pytest.fixture
def mock_standard_set_data():
    """Create mock standard set data for testing."""
    return create_standard_set_test_data()


@pytest.fixture
def mock_classifications():
    """Create mock classification data for testing."""
    return create_classification_test_data()


@pytest.fixture
def mock_standards(mock_standard_set_data, mock_classifications):
    """Create mock standards data for testing."""
    return [
        create_standard_test_data(
            mock_standard_set_data["_id"],
            [mock_classifications[0]["_id"]]  # Python standard
        ),
        create_standard_test_data(
            mock_standard_set_data["_id"],
            [mock_classifications[1]["_id"]]  # Security standard
        ),
        create_standard_test_data(
            mock_standard_set_data["_id"],
            []  # Universal standard
        )
    ]


@pytest.fixture
def mock_markdown_files():
    """Create mock markdown files for testing."""
    return [
        {
            "filename": "python_standard.md",
            "content": """# Python Code Standard
This standard applies to Python code quality.
## Requirements
- Use type hints
- Follow PEP 8
- Document all functions"""
        },
        {
            "filename": "security_standard.md",
            "content": """# Security Standard
This standard applies to code security.
## Requirements
- Use secure dependencies
- Validate all inputs
- Encrypt sensitive data"""
        },
        {
            "filename": "universal_standard.md",
            "content": """# Universal Standard
This standard applies to all code.
## Requirements
- Use version control
- Write tests
- Document changes"""
        }
    ]


@pytest.fixture
def mock_collections(mock_database_setup, mock_standard_set_data, mock_classifications, mock_standards):
    """Setup mock collections with initial data and behaviors."""
    # Create mock collections
    standard_sets_collection = AsyncMock()
    standards_collection = AsyncMock()
    classifications_collection = AsyncMock()

    # Configure standards collection behaviors
    standards_collection.insert_one = AsyncMock(
        return_value=AsyncMock(inserted_id=ObjectId()))
    standards_collection.delete_many = AsyncMock(
        return_value=AsyncMock(deleted_count=1))

    # Configure find operations with proper cursor mocking
    standards_cursor = AsyncMock()
    standards_cursor.to_list = AsyncMock(return_value=mock_standards)
    standards_collection.find = MagicMock(return_value=standards_cursor)

    # Configure classifications collection behaviors
    classifications_cursor = AsyncMock()
    classifications_cursor.to_list = AsyncMock(
        return_value=mock_classifications)
    classifications_collection.find = MagicMock(
        return_value=classifications_cursor)

    # Mock database property for nested collections
    mock_db = AsyncMock()
    type(standards_collection).database = PropertyMock(return_value=mock_db)
    type(classifications_collection).database = PropertyMock(return_value=mock_db)
    type(standard_sets_collection).database = PropertyMock(return_value=mock_db)

    # Configure mock database setup
    mock_database_setup.get_collection = MagicMock(side_effect=lambda name: {
        "standard_sets": standard_sets_collection,
        "standards": standards_collection,
        "classifications": classifications_collection
    }[name])

    # Configure collection methods for repository pattern
    standard_sets_collection.find_one = AsyncMock(
        return_value=mock_standard_set_data)
    standard_sets_collection.find_one_and_update = AsyncMock(
        return_value=mock_standard_set_data)
    standard_sets_collection.find_one_and_replace = AsyncMock(
        return_value=mock_standard_set_data)

    return standard_sets_collection, standards_collection, classifications_collection


@pytest.fixture(autouse=True)
async def setup_and_teardown():
    """Setup and teardown for each test."""
    # Setup
    yield
    # Teardown - clear dependency overrides
    from src.main import app
    app.dependency_overrides = {}


@pytest.fixture
def mock_database_setup():
    """Setup mock database."""
    mock_db = AsyncMock()
    mock_db.get_collection = AsyncMock()
    return mock_db


@pytest.mark.asyncio
async def test_mock_collections_setup(mock_collections, mock_standard_set_data, mock_classifications, mock_standards):
    """Test that mock collections are configured correctly."""
    # Given: Mock collections
    standard_sets_collection, standards_collection, classifications_collection = mock_collections

    # When/Then: Verify standard_sets collection setup
    result = await standard_sets_collection.find_one({"_id": mock_standard_set_data["_id"]})
    assert result == mock_standard_set_data

    # When/Then: Verify classifications collection setup
    classifications = await classifications_collection.find().to_list(None)
    assert classifications == mock_classifications

    # When/Then: Verify standards collection setup
    standards = await standards_collection.find().to_list(None)
    assert standards == mock_standards


@pytest.mark.asyncio
async def test_process_standard_set_success(
    mock_database_setup,
    mock_collections,
    mock_standard_set_data,
    mock_classifications,
    mock_markdown_files
):
    """Test successful processing of a standard set."""
    # Given
    standard_sets_collection, standards_collection, classifications_collection = mock_collections

    # Mock repositories
    mock_standard_set_repo = AsyncMock()
    mock_standard_set_repo.get_by_id = AsyncMock(
        return_value=mock_standard_set_data)
    mock_standard_set_repo.delete_many = AsyncMock(return_value=1)
    mock_standard_set_repo.insert_one = AsyncMock(return_value=ObjectId())

    mock_classification_repo = AsyncMock()
    mock_classification_repo.get_all = AsyncMock(
        return_value=mock_classifications)

    # Mock database initialization and repository creation
    with patch('src.agents.standards_agent.get_database', return_value=mock_database_setup), \
            patch('src.agents.standards_agent.download_repository') as mock_download, \
            patch('src.agents.standards_agent.analyze_standard', return_value=[mock_classifications[0]["name"]]), \
            patch('src.agents.standards_agent.cleanup_repository') as mock_cleanup, \
            patch('src.repositories.standard_set_repo.StandardSetRepository', return_value=mock_standard_set_repo), \
            patch('src.repositories.classification_repo.ClassificationRepository', return_value=mock_classification_repo), \
            patch('src.agents.standards_agent.get_classifications', return_value=mock_classifications):

        # Create temp directory and mock its creation
        temp_dir = Path(tempfile.mkdtemp())
        mock_download.return_value = temp_dir

        # Create mock markdown files in temp directory
        for file_data in mock_markdown_files:
            file_path = temp_dir / file_data["filename"]
            file_path.write_text(file_data["content"])

        # When: Process standard set
        standard_set_id = str(mock_standard_set_data["_id"])
        await process_standard_set(
            standard_set_id,
            mock_standard_set_data["repository_url"]
        )

        # Then: Verify repository operations
        mock_cleanup.assert_called_once_with(temp_dir)
        mock_download.assert_called_once_with(
            mock_standard_set_data["repository_url"])


@pytest.mark.asyncio
async def test_process_standard_set_database_error(
    mock_database_setup,
    mock_collections,
    mock_standard_set_data
):
    """Test handling of database errors during standard set processing."""
    # Given: Database error during initialization
    with patch('src.agents.standards_agent.get_database', side_effect=Exception("Database connection error")):
        # When/Then: Process should handle error
        with pytest.raises(Exception) as exc_info:
            await process_standard_set(
                str(mock_standard_set_data["_id"]),
                mock_standard_set_data["repository_url"]
            )

        assert "Database connection error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_process_standard_set_git_error(
    mock_database_setup,
    mock_collections,
    mock_standard_set_data
):
    """Test handling of Git operation errors."""
    # Given: Git clone error
    standard_sets_collection, standards_collection, classifications_collection = mock_collections

    # Configure mock database setup
    mock_database_setup.get_collection = MagicMock(side_effect=lambda name: {
        "standard_sets": standard_sets_collection,
        "standards": standards_collection,
        "classifications": classifications_collection
    }[name])

    with patch('src.agents.standards_agent.get_database', return_value=mock_database_setup), \
            patch('src.agents.standards_agent.clone_repo', side_effect=Exception("Git clone failed")):

        # When/Then: Process should handle error
        with pytest.raises(Exception) as exc_info:
            await process_standard_set(
                str(mock_standard_set_data["_id"]),
                mock_standard_set_data["repository_url"]
            )

        assert "Git clone failed" in str(exc_info.value)
