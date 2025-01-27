"""Unit tests for StandardSetRepository."""
import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import OperationFailure
from src.repositories.standard_set_repo import StandardSetRepository
from src.models.standard_set import StandardSetCreate, StandardSet, StandardSetWithStandards
from src.repositories.errors import RepositoryError, DatabaseError

@pytest.fixture
def standard_set_data():
    return {
        "name": "Test Standard Set",
        "description": "Test Description",
        "version": "1.0.0",
        "repository_url": "https://github.com/test/repo",
        "custom_prompt": "Test prompt"
    }

@pytest.fixture
def mock_collection():
    collection = AsyncMock()
    collection.database.client.start_session = AsyncMock()
    collection.database.get_collection = Mock(return_value=AsyncMock())
    return collection

@pytest.fixture
def repo(mock_collection):
    return StandardSetRepository(mock_collection)

class AsyncIteratorMock:
    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return self.items.pop(0)
        except IndexError:
            raise StopAsyncIteration

class AsyncContextManager:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.mark.asyncio
async def test_create_with_session_existing_set(repo, standard_set_data):
    # Setup
    standard_set = StandardSetCreate(**standard_set_data)
    existing_id = ObjectId()
    existing = {"_id": existing_id, "name": standard_set.name}
    
    repo.collection.find_one = AsyncMock(return_value=existing)
    repo.collection.find_one_and_replace = AsyncMock(return_value={
        "_id": existing_id,
        **standard_set_data,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    })

    # Execute
    result = await repo._create_with_session(standard_set)

    # Verify
    assert result["name"] == standard_set.name
    repo.standards_collection.delete_many.assert_called_once()

@pytest.mark.asyncio
async def test_create_with_session_new_set(repo, standard_set_data):
    # Setup
    standard_set = StandardSetCreate(**standard_set_data)
    repo.collection.find_one = AsyncMock(return_value=None)
    repo.collection.find_one_and_replace = AsyncMock(return_value=None)

    # Execute
    result = await repo._create_with_session(standard_set)

    # Verify
    assert result["name"] == standard_set.name
    assert "_id" in result
    repo.standards_collection.delete_many.assert_not_called()

@pytest.mark.asyncio
async def test_create_with_transaction(repo, standard_set_data):
    # Setup
    standard_set = StandardSetCreate(**standard_set_data)
    
    # Mock session
    session = AsyncContextManager()
    repo.collection.database.client.start_session.return_value = session
    
    # Mock transaction
    session.start_transaction = Mock(return_value=AsyncContextManager())
    
    # First attempt fails with non-Mongomock error
    repo._create_with_session = AsyncMock(side_effect=[
        Exception("Database error"),  # First attempt fails
        {"_id": ObjectId(), **standard_set_data}  # Second attempt succeeds
    ])

    # Execute
    result = await repo.create(standard_set)

    # Verify
    assert isinstance(result, StandardSet)
    assert result.name == standard_set_data["name"]
    assert repo._create_with_session.call_count == 2
    assert repo.collection.database.client.start_session.called
    assert session.start_transaction.called

@pytest.mark.asyncio
async def test_create_with_mongomock_error(repo, standard_set_data):
    # Setup
    standard_set = StandardSetCreate(**standard_set_data)
    
    # First attempt fails with Mongomock error
    repo._create_with_session = AsyncMock(side_effect=[
        Exception("Mongomock does not support sessions"),  # First attempt fails
        {"_id": ObjectId(), **standard_set_data}  # Second attempt succeeds
    ])

    # Execute
    result = await repo.create(standard_set)

    # Verify
    assert isinstance(result, StandardSet)
    assert result.name == standard_set_data["name"]
    assert repo._create_with_session.call_count == 2
    repo.collection.database.client.start_session.assert_not_called()

@pytest.mark.asyncio
async def test_create_error(repo, standard_set_data):
    # Setup
    standard_set = StandardSetCreate(**standard_set_data)
    
    # Mock session
    session = AsyncContextManager()
    repo.collection.database.client.start_session.return_value = session
    
    # Mock transaction
    session.start_transaction = Mock(return_value=AsyncContextManager())
    
    # Mock error
    repo._create_with_session = AsyncMock(side_effect=Exception("Database error"))

    # Execute and verify
    with pytest.raises(RepositoryError, match="Failed to create standard set"):
        await repo.create(standard_set)

@pytest.mark.asyncio
async def test_get_all_empty(repo):
    # Setup
    repo.collection.find = Mock(return_value=AsyncIteratorMock([]))

    # Execute
    result = await repo.get_all()

    # Verify
    assert result == []

@pytest.mark.asyncio
async def test_get_all_with_items(repo):
    # Setup
    mock_items = [{"_id": ObjectId(), "name": "Set 1"}, {"_id": ObjectId(), "name": "Set 2"}]
    repo.collection.find = Mock(return_value=AsyncIteratorMock(mock_items.copy()))

    # Execute
    result = await repo.get_all()

    # Verify
    assert len(result) == 2
    assert all(item["name"] in ["Set 1", "Set 2"] for item in result)

@pytest.mark.asyncio
async def test_update_not_found(repo, standard_set_data):
    # Setup
    standard_set = StandardSetCreate(**standard_set_data)
    repo.find_by_name = AsyncMock(return_value=None)

    # Execute and verify
    with pytest.raises(RepositoryError, match="Standard set not found"):
        await repo.update(standard_set)

@pytest.mark.asyncio
async def test_update_success(repo, standard_set_data):
    # Setup
    standard_set = StandardSetCreate(**standard_set_data)
    existing = StandardSet(
        id=str(ObjectId()),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        **standard_set_data
    )
    repo.find_by_name = AsyncMock(return_value=existing)
    repo.collection.replace_one = AsyncMock(return_value=Mock(modified_count=1))

    # Execute
    result = await repo.update(standard_set)

    # Verify
    assert isinstance(result, StandardSet)
    assert result.name == standard_set.name

@pytest.mark.asyncio
async def test_update_failed(repo, standard_set_data):
    # Setup
    standard_set = StandardSetCreate(**standard_set_data)
    existing = StandardSet(
        id=str(ObjectId()),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        **standard_set_data
    )
    repo.find_by_name = AsyncMock(return_value=existing)
    repo.collection.replace_one = AsyncMock(return_value=Mock(modified_count=0))

    # Execute and verify
    with pytest.raises(RepositoryError, match="Failed to update standard set"):
        await repo.update(standard_set)

@pytest.mark.asyncio
async def test_find_by_name_success(repo, standard_set_data):
    # Setup
    test_id = ObjectId()
    doc = {
        "_id": test_id,
        **standard_set_data,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    repo.collection.find_one = AsyncMock(return_value=doc)

    # Execute
    result = await repo.find_by_name(standard_set_data["name"])

    # Verify
    assert isinstance(result, StandardSet)
    assert result.name == standard_set_data["name"]

@pytest.mark.asyncio
async def test_find_by_name_not_found(repo):
    # Setup
    repo.collection.find_one = AsyncMock(return_value=None)

    # Execute
    result = await repo.find_by_name("test")

    # Verify
    assert result is None

@pytest.mark.asyncio
async def test_find_by_name_error(repo):
    # Setup
    repo.collection.find_one = AsyncMock(side_effect=Exception("Database error"))

    # Execute and verify
    with pytest.raises(RepositoryError, match="Error finding standard set by name"):
        await repo.find_by_name("test")

@pytest.mark.asyncio
async def test_get_by_id_not_found(repo):
    # Setup
    repo.collection.find_one = AsyncMock(return_value=None)

    # Execute
    result = await repo.get_by_id(ObjectId())

    # Verify
    assert result is None

@pytest.mark.asyncio
async def test_get_by_id_success(repo, standard_set_data):
    # Setup
    test_id = ObjectId()
    standard_set_doc = {
        "_id": test_id,
        **standard_set_data,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    standards = [{
        "_id": ObjectId(),
        "text": "Test standard text",
        "repository_path": "/test/path.md",
        "standard_set_id": str(test_id),
        "classification_ids": []
    }]
    
    repo.collection.find_one = AsyncMock(return_value=standard_set_doc)
    
    # Create a mock cursor with to_list method
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=standards)
    repo.standards_collection.find = Mock(return_value=mock_cursor)

    # Execute
    result = await repo.get_by_id(test_id)

    # Verify
    assert isinstance(result, StandardSetWithStandards)
    assert result.name == standard_set_data["name"]
    assert len(result.standards) == 1
    assert result.standards[0].text == "Test standard text"
    assert result.standards[0].repository_path == "/test/path.md"

@pytest.mark.asyncio
async def test_get_by_id_error(repo):
    # Setup
    repo.collection.find_one = AsyncMock(side_effect=Exception("Database error"))

    # Execute and verify
    with pytest.raises(RepositoryError, match="Error getting standard set by ID"):
        await repo.get_by_id(ObjectId())

@pytest.mark.asyncio
async def test_delete_success(repo):
    # Setup
    test_id = ObjectId()
    repo.standards_collection.delete_many = AsyncMock()
    repo.collection.delete_one = AsyncMock(return_value=Mock(deleted_count=1))

    # Execute
    result = await repo.delete(test_id)

    # Verify
    assert result is True
    repo.standards_collection.delete_many.assert_called_once()
    repo.collection.delete_one.assert_called_once()

@pytest.mark.asyncio
async def test_delete_not_found(repo):
    # Setup
    test_id = ObjectId()
    repo.standards_collection.delete_many = AsyncMock()
    repo.collection.delete_one = AsyncMock(return_value=Mock(deleted_count=0))

    # Execute
    result = await repo.delete(test_id)

    # Verify
    assert result is False

@pytest.mark.asyncio
async def test_delete_error(repo):
    # Setup
    test_id = ObjectId()
    repo.standards_collection.delete_many = AsyncMock(side_effect=Exception("Database error"))

    # Execute and verify
    with pytest.raises(DatabaseError, match="Failed to delete standard set"):
        await repo.delete(test_id) 