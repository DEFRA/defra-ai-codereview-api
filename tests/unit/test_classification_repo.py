"""Unit tests for the classification repository."""
import pytest
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock, AsyncMock
from bson import ObjectId
from src.models.classification import Classification, ClassificationCreate
from src.repositories.classification_repo import ClassificationRepository

@pytest.fixture
def mock_collection():
    """Create a mock MongoDB collection."""
    return MagicMock()

@pytest.fixture
def repo(mock_collection):
    """Create a ClassificationRepository instance with a mock collection."""
    return ClassificationRepository(mock_collection)

@pytest.mark.asyncio
async def test_create_handles_database_error(repo):
    """Test create method handles database errors gracefully."""
    # Given
    classification = ClassificationCreate(name="Test")
    repo.collection.insert_one.side_effect = Exception("Database error")

    # When/Then
    with pytest.raises(Exception) as exc_info:
        await repo.create(classification)
    assert str(exc_info.value) == "Database error"

@pytest.mark.asyncio
async def test_get_by_id_handles_invalid_id(repo):
    """Test get_by_id method handles invalid ObjectId."""
    # Given
    invalid_id = "invalid-id"

    # When
    result = await repo.get_by_id(invalid_id)

    # Then
    assert result is None
    repo.collection.find_one.assert_not_called()

@pytest.mark.asyncio
async def test_get_by_id_handles_database_error(repo):
    """Test get_by_id method handles database errors gracefully."""
    # Given
    valid_id = str(ObjectId())
    repo.collection.find_one.side_effect = Exception("Database error")

    # When
    result = await repo.get_by_id(valid_id)

    # Then
    assert result is None

@pytest.mark.asyncio
async def test_get_all_handles_database_error(repo):
    """Test get_all method handles database errors gracefully."""
    # Given
    repo.collection.find.side_effect = Exception("Database error")

    # When/Then
    with pytest.raises(Exception) as exc_info:
        await repo.get_all()
    assert str(exc_info.value) == "Database error"

@pytest.mark.asyncio
async def test_get_all_handles_invalid_document(repo):
    """Test get_all method handles invalid documents gracefully."""
    # Given
    invalid_doc = {"_id": ObjectId(), "invalid_field": "value"}  # Missing required 'name' field
    mock_cursor = MagicMock()
    mock_cursor.__aiter__.return_value = [invalid_doc]
    repo.collection.find.return_value = mock_cursor

    # When
    result = await repo.get_all()

    # Then
    assert result == []  # Invalid document should be skipped

@pytest.mark.asyncio
async def test_delete_handles_invalid_id_format(repo):
    """Test delete method handles invalid ID format."""
    # Given
    invalid_id = "invalid-id"

    # When/Then
    with pytest.raises(ValueError) as exc_info:
        await repo.delete(invalid_id)
    assert str(exc_info.value) == "Invalid ObjectId format"
    repo.collection.delete_one.assert_not_called()

@pytest.mark.asyncio
async def test_delete_handles_database_error(repo):
    """Test delete method handles database errors gracefully."""
    # Given
    valid_id = str(ObjectId())
    repo.collection.delete_one.side_effect = Exception("Database error")

    # When
    result = await repo.delete(valid_id)

    # Then
    assert result is False

@pytest.mark.asyncio
async def test_update_handles_invalid_id(repo):
    """Test update method handles invalid ObjectId."""
    # Given
    invalid_id = "invalid-id"
    classification = ClassificationCreate(name="Test")

    # When
    result = await repo.update(invalid_id, classification)

    # Then
    assert result is None
    repo.collection.update_one.assert_not_called()

@pytest.mark.asyncio
async def test_update_handles_database_error(repo):
    """Test update method handles database errors gracefully."""
    # Given
    valid_id = str(ObjectId())
    classification = ClassificationCreate(name="Test")
    repo.collection.update_one.side_effect = Exception("Database error")

    # When
    result = await repo.update(valid_id, classification)

    # Then
    assert result is None 

@pytest.mark.asyncio
async def test_create_success(repo):
    """Test successful creation of a classification."""
    # Given
    classification = ClassificationCreate(name="Test")
    mock_id = ObjectId()
    repo.collection.insert_one = AsyncMock()

    # When
    result = await repo.create(classification)

    # Then
    assert isinstance(result, Classification)
    assert result.name == "Test"
    assert isinstance(result.created_at, datetime)
    assert isinstance(result.updated_at, datetime)
    repo.collection.insert_one.assert_called_once()

@pytest.mark.asyncio
async def test_update_success(repo):
    """Test successful update of a classification."""
    # Given
    valid_id = str(ObjectId())
    classification = ClassificationCreate(name="Updated Test")
    mock_updated_doc = {
        "_id": ObjectId(valid_id),
        "name": "Updated Test",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    
    repo.collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    repo.collection.find_one = AsyncMock(return_value=mock_updated_doc)

    # When
    result = await repo.update(valid_id, classification)

    # Then
    assert isinstance(result, Classification)
    assert result.name == "Updated Test"
    repo.collection.update_one.assert_called_once() 

@pytest.mark.asyncio
async def test_get_by_id_returns_classification_when_found(repo):
    """Test get_by_id method successfully returns a classification when found."""
    # Given
    valid_id = str(ObjectId())
    mock_doc = {
        "_id": ObjectId(valid_id),
        "name": "Test",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    repo.collection.find_one = AsyncMock(return_value=mock_doc)

    # When
    result = await repo.get_by_id(valid_id)

    # Then
    assert isinstance(result, Classification)
    assert result.name == "Test"
    repo.collection.find_one.assert_called_once_with({"_id": ObjectId(valid_id)})

@pytest.mark.asyncio
async def test_update_returns_none_when_no_document_updated(repo):
    """Test update method returns None when no document is updated."""
    # Given
    valid_id = str(ObjectId())
    classification = ClassificationCreate(name="Test")
    repo.collection.update_one = AsyncMock(return_value=MagicMock(modified_count=0))

    # When
    result = await repo.update(valid_id, classification)

    # Then
    assert result is None
    repo.collection.update_one.assert_called_once() 

@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_not_found(repo):
    """Test get_by_id method returns None when no document is found."""
    # Given
    valid_id = str(ObjectId())
    repo.collection.find_one = AsyncMock(return_value=None)

    # When
    result = await repo.get_by_id(valid_id)

    # Then
    assert result is None
    repo.collection.find_one.assert_called_once_with({"_id": ObjectId(valid_id)}) 