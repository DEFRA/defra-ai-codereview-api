'''Integration tests for the standards agent.

Tests cover the standards agent functionality while mocking MongoDB interactions.'''
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from bson import ObjectId
from datetime import datetime, UTC
from pathlib import Path
import tempfile
from src.models.standard_set import StandardSet, StandardSetCreate
from src.models.classification import Classification
from src.repositories.standard_set_repo import StandardSetRepository
from src.services.standard_set_service import StandardSetService
from src.agents.standards_agent import process_standard_set, StandardsProcessingError
from src.database.database_utils import get_database
from tests.utils.test_data import (
    create_standard_set_test_data,
    create_classification_test_data,
    create_standard_test_data
)
import shutil


# Test Setup and Fixtures


@pytest.fixture(autouse=True)
async def setup_and_teardown():
    '''Setup and teardown for each test.'''
    # Setup
    with patch('src.database.database_utils.init_database') as mock_init_db:
        mock_db = AsyncMock()
        mock_init_db.return_value = mock_db
        yield
    # Teardown - clear dependency overrides
    from src.main import app
    app.dependency_overrides = {}


@pytest.fixture
async def mock_collections():
    '''Setup mock collections for tests.'''
    standard_sets_collection = AsyncMock()
    standards_collection = AsyncMock()
    classifications_collection = AsyncMock()

    # Mock the database property for nested collections
    mock_db = AsyncMock()
    mock_db.get_collection = MagicMock(side_effect=lambda name: {
        "standards": standards_collection,
        "classifications": classifications_collection,
        "standard_sets": standard_sets_collection
    }[name])
    type(standard_sets_collection).database = PropertyMock(return_value=mock_db)
    type(standards_collection).database = PropertyMock(return_value=mock_db)
    type(classifications_collection).database = PropertyMock(return_value=mock_db)

    # Configure standards collection for standard set repository
    standards_cursor = AsyncMock()
    standards_cursor.to_list = AsyncMock(return_value=[])
    standards_collection.find = MagicMock(return_value=standards_cursor)

    return standard_sets_collection, standards_collection, classifications_collection


@pytest.fixture
def setup_service(mock_database_setup, mock_collections):
    '''Helper fixture to setup service with mocked dependencies.'''
    standard_sets_collection, standards_collection, classifications_collection = mock_collections
    mock_database_setup.standard_sets = standard_sets_collection
    mock_database_setup.standards = standards_collection
    mock_database_setup.classifications = classifications_collection

    repo = StandardSetRepository(standard_sets_collection)
    service = StandardSetService(mock_database_setup, repo)

    return service, standard_sets_collection, standards_collection, classifications_collection


@pytest.fixture
def setup_mock_result(operation_type="insert", count=1, doc_id=None):
    '''Helper fixture to setup mock results for database operations.'''
    class MockResult:
        def __init__(self):
            if operation_type == "insert":
                self.inserted_id = doc_id or ObjectId()
            elif operation_type == "update":
                self.modified_count = count
                self.matched_count = count
            elif operation_type == "delete":
                self.deleted_count = count

    return MockResult()


@pytest.fixture
def setup_error_mock(error_message="Database error"):
    '''Helper fixture to setup error mocks for database operations.'''
    return AsyncMock(side_effect=Exception(error_message))


# Test Data Constants
TEST_REPO_URL = "https://github.com/test/standards-repo"
TEST_PROMPT = "Test prompt for standards analysis"


def create_standard_set_test_data(set_id: ObjectId = None) -> dict:
    '''Create a standard set test document with consistent structure.'''
    return {
        "_id": set_id or ObjectId(),
        "name": "Test Standard Set",
        "repository_url": TEST_REPO_URL,
        "custom_prompt": TEST_PROMPT,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }


def create_classification_test_data() -> list[dict]:
    '''Create a set of test classifications with consistent structure.'''
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
    '''Create a standard test document with consistent structure.'''
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
    '''Create mock standard set data for testing.'''
    return create_standard_set_test_data()


@pytest.fixture
def mock_classifications():
    '''Create mock classification data for testing.'''
    return create_classification_test_data()


@pytest.fixture
def mock_standards(mock_standard_set_data, mock_classifications):
    '''Create mock standards data for testing.'''
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
    '''Create mock markdown files for testing.'''
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
async def mock_collections_with_data(mock_database_setup, mock_standard_set_data, mock_classifications, mock_standards):
    '''Setup mock collections with initial data and behaviors.'''
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

    # Await any async setup
    await standards_cursor.to_list(None)
    await classifications_cursor.to_list(None)

    return standard_sets_collection, standards_collection, classifications_collection


@pytest.fixture
def mock_database_setup():
    '''Setup mock database.'''
    mock_db = AsyncMock()
    mock_db.get_collection = AsyncMock()
    return mock_db


@pytest.mark.asyncio
async def test_mock_collections_setup(mock_collections, mock_standard_set_data, mock_classifications, mock_standards):
    '''Test that mock collections are configured correctly.'''
    # Given: Mock collections
    standard_sets_collection, standards_collection, classifications_collection = mock_collections

    # Configure collection behaviors
    standard_sets_collection.find_one = AsyncMock(
        return_value=mock_standard_set_data)

    standards_cursor = AsyncMock()
    standards_cursor.to_list = AsyncMock(return_value=mock_standards)
    standards_collection.find = MagicMock(return_value=standards_cursor)

    classifications_cursor = AsyncMock()
    classifications_cursor.to_list = AsyncMock(
        return_value=mock_classifications)
    classifications_collection.find = MagicMock(
        return_value=classifications_cursor)

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
    setup_service,
    setup_mock_result
):
    '''Test successful processing of a standard set.'''
    # Given: Mock data and service setup
    _, standard_sets_collection, standards_collection, classifications_collection = setup_service
    standard_set_data = create_standard_set_test_data()
    classifications = create_classification_test_data()

    # Configure collection behaviors
    standard_sets_collection.find_one = AsyncMock(
        return_value=standard_set_data)

    # Configure standards collection
    standards_cursor = AsyncMock()
    standards_cursor.to_list = AsyncMock(return_value=[])
    standards_collection.find = MagicMock(return_value=standards_cursor)
    standards_collection.insert_one = AsyncMock(return_value=setup_mock_result)
    standards_collection.delete_many = AsyncMock(
        return_value=AsyncMock(deleted_count=1))

    # Configure classifications collection
    classifications_cursor = AsyncMock()
    classifications_cursor.to_list = AsyncMock(return_value=classifications)
    classifications_collection.find = MagicMock(
        return_value=classifications_cursor)

    # Configure database get_collection to return properly mocked collections
    def get_collection_mock(name):
        collection_map = {
            "standards": standards_collection,
            "classifications": classifications_collection,
            "standard_sets": standard_sets_collection
        }
        collection = collection_map[name]
        # Ensure find returns a cursor synchronously
        if isinstance(collection.find, AsyncMock):
            collection.find = MagicMock(return_value=AsyncMock(
                to_list=AsyncMock(return_value=[])))
        return collection

    mock_database_setup.get_collection = MagicMock(
        side_effect=get_collection_mock)

    # Create temp directory and mock files
    temp_dir = Path(tempfile.mkdtemp())
    for i in range(3):
        file_path = temp_dir / f"standard_{i}.md"
        file_path.write_text(f"# Standard {i}\nTest content for standard {i}")

    # Mock repository operations and database
    with patch('src.agents.standards_agent.get_database', return_value=mock_database_setup), \
            patch('src.agents.standards_agent.download_repository', return_value=temp_dir), \
            patch('src.agents.standards_agent.analyze_standard', return_value=[classifications[0]["name"]]), \
            patch('src.agents.standards_agent.cleanup_repository') as mock_cleanup, \
            patch('src.agents.standards_agent.get_files_to_process') as mock_get_files, \
            patch('src.repositories.standard_set_repo.StandardSetRepository.get_by_id') as mock_get_by_id:

        # Configure test mode
        mock_get_files.return_value = [
            (str(temp_dir), "standard_0.md"),
            (str(temp_dir), "standard_1.md"),
            (str(temp_dir), "standard_2.md")
        ]

        # Configure get_by_id mock
        mock_get_by_id.return_value = standard_set_data

        # When: Process standard set
        await process_standard_set(
            str(standard_set_data["_id"]),
            standard_set_data["repository_url"]
        )

        # Then: Verify operations
        mock_cleanup.assert_called_once_with(temp_dir)
        standards_collection.delete_many.assert_called_once()
        assert standards_collection.insert_one.call_count == 3

        # Cleanup
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_process_standard_set_database_error(
    mock_database_setup,
    setup_service,
    setup_error_mock
):
    '''Test handling of database errors during standard set processing.'''
    # Given: Database error during initialization
    with patch('src.agents.standards_agent.get_database', side_effect=Exception("Database error")):
        # When/Then: Process should handle error
        with pytest.raises(Exception) as exc_info:
            await process_standard_set(
                str(ObjectId()),
                "https://github.com/test/repo"
            )

        assert "Database error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_process_standard_set_git_error(
    mock_database_setup,
    setup_service
):
    '''Test handling of Git operation errors.'''
    # Given: Git clone error
    _, standard_sets_collection, _, _ = setup_service
    standard_set_data = create_standard_set_test_data()
    standard_sets_collection.find_one = AsyncMock(
        return_value=standard_set_data)

    with patch('src.agents.standards_agent.get_database', return_value=mock_database_setup), \
            patch('src.agents.standards_agent.download_repository', side_effect=Exception("Git clone failed")), \
            patch('src.repositories.standard_set_repo.StandardSetRepository.get_by_id') as mock_get_by_id:

        # Configure get_by_id mock
        mock_get_by_id.return_value = standard_set_data

        # When/Then: Process should handle error
        with pytest.raises(Exception) as exc_info:
            await process_standard_set(
                str(standard_set_data["_id"]),
                standard_set_data["repository_url"]
            )

        # Ensure all async mocks are awaited
        await standard_sets_collection.find_one()
        assert "Git clone failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_process_standard_set_invalid_id(
    mock_database_setup,
    setup_service
):
    '''Test handling of invalid ObjectId.'''
    # Given: Invalid ObjectId format
    invalid_id = "invalid-id"
    _, standard_sets_collection, _, _ = setup_service

    # Mock database operations and repository download
    with patch('src.agents.standards_agent.get_database', return_value=mock_database_setup), \
            patch('src.agents.standards_agent.download_repository', side_effect=StandardsProcessingError("Invalid ObjectId format")):
        # When/Then: Process should handle error
        with pytest.raises(StandardsProcessingError) as exc_info:
            await process_standard_set(
                invalid_id,
                "https://github.com/test/repo"
            )

        await standard_sets_collection.find_one()
        assert "Invalid ObjectId format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_process_standard_set_not_found(
    mock_database_setup,
    setup_service
):
    '''Test handling of non-existent standard set.'''
    # Given: Standard set not found
    _, standard_sets_collection, _, _ = setup_service
    standard_sets_collection.find_one = AsyncMock(return_value=None)
    set_id = str(ObjectId())

    # Mock database operations and repository download
    with patch('src.agents.standards_agent.get_database', return_value=mock_database_setup), \
            patch('src.agents.standards_agent.download_repository', side_effect=StandardsProcessingError("Standard set not found")):
        # When/Then: Process should handle error
        with pytest.raises(StandardsProcessingError) as exc_info:
            await process_standard_set(
                set_id,
                "https://github.com/test/repo"
            )

        await standard_sets_collection.find_one()
        assert "Standard set not found" in str(exc_info.value)
