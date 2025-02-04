"""Unit tests for ClassificationRepository."""
import pytest
from datetime import datetime, UTC
from bson import ObjectId
from unittest.mock import AsyncMock, MagicMock
from src.repositories.classification_repo import ClassificationRepository
from src.models.classification import ClassificationCreate, Classification
from src.repositories.errors import DatabaseError

@pytest.fixture
def classification_repo():
    """Create a ClassificationRepository instance with mocked collection."""
    return ClassificationRepository(AsyncMock())

class TestClassificationRepository:
    """Tests for ClassificationRepository."""
    
    async def test_create_success(
        self,
        classification_repo
    ):
        # Given: Valid classification data and no existing classification
        doc_id = ObjectId()
        now = datetime.now(UTC)
        
        # Mock get_by_name to return None (no existing classification)
        classification_repo.collection.find_one = AsyncMock(return_value=None)
        
        # Mock insert_one to succeed
        classification_repo.collection.insert_one = AsyncMock()
        
        # When: Creating a new classification
        classification = ClassificationCreate(name="Test Classification")
        result = await classification_repo.create(classification)
        
        # Then: Classification is created successfully
        assert isinstance(result, Classification)
        assert result.name == "Test Classification"
        assert isinstance(result.id, str)
        assert isinstance(result.created_at, datetime)
        assert isinstance(result.updated_at, datetime)
        
        # Verify operations were called correctly
        classification_repo.collection.find_one.assert_called_once_with(
            {"name": "Test Classification"}
        )
        classification_repo.collection.insert_one.assert_called_once()

    async def test_create_handles_duplicate(
        self,
        classification_repo
    ):
        # Given: Existing classification with same name
        doc_id = ObjectId()
        now = datetime.now(UTC)
        
        # Create a document that matches the Classification model
        mock_doc = {
            "_id": doc_id,
            "name": "Test Classification",
            "created_at": now,
            "updated_at": now
        }
        
        # Mock the find_one operation for get_by_name
        classification_repo.collection.find_one = AsyncMock(return_value=mock_doc)
        
        # When: Creating a classification with same name
        classification = ClassificationCreate(name="Test Classification")
        result = await classification_repo.create(classification)
        
        # Then: Returns existing classification
        assert isinstance(result, Classification)
        assert result.name == mock_doc["name"]
        assert result.id == str(doc_id)
        assert result.created_at == now
        assert result.updated_at == now
        
        # Verify find_one was called with correct parameters
        classification_repo.collection.find_one.assert_called_once_with({"name": "Test Classification"})

    async def test_create_handles_error(
        self,
        classification_repo
    ):
        # Given: Database operation fails
        # Mock get_by_name to return None (no existing classification)
        classification_repo.collection.find_one = AsyncMock(return_value=None)
        
        # Mock insert_one to raise an exception
        classification_repo.collection.insert_one = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        # When/Then: Creating fails gracefully
        with pytest.raises(Exception) as exc_info:
            await classification_repo.create(ClassificationCreate(name="Test"))
            
        assert str(exc_info.value) == "Database error"
        
        # Verify the operations were called
        classification_repo.collection.find_one.assert_called_once_with({"name": "Test"})
        classification_repo.collection.insert_one.assert_called_once()

    async def test_get_all_success(
        self,
        classification_repo
    ):
        # Given: Multiple classifications exist
        now = datetime.now(UTC)
        mock_docs = [
            {
                "_id": ObjectId(),
                "name": f"Test {i}",
                "created_at": now,
                "updated_at": now
            }
            for i in range(3)
        ]
        
        # Mock find operation with cursor
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_docs)
        classification_repo.collection.find = MagicMock(return_value=mock_cursor)
        
        # When: Getting all classifications
        results = await classification_repo.get_all()
        
        # Then: Returns list of classifications
        assert len(results) == 3
        assert all(isinstance(r, Classification) for r in results)
        assert [r.name for r in results] == ["Test 0", "Test 1", "Test 2"]
        
        # Verify find was called
        classification_repo.collection.find.assert_called_once_with()

    async def test_get_by_id_success(
        self,
        classification_repo
    ):
        # Given: Classification exists
        doc_id = ObjectId()
        now = datetime.now(UTC)
        mock_doc = {
            "_id": doc_id,
            "name": "Test",
            "created_at": now,
            "updated_at": now
        }
        
        # Mock find_one operation
        classification_repo.collection.find_one = AsyncMock(return_value=mock_doc)
        
        # When: Getting by ID
        result = await classification_repo.get_by_id(str(doc_id))
        
        # Then: Returns correct classification
        assert isinstance(result, Classification)
        assert result.id == str(doc_id)
        assert result.name == "Test"
        
        # Verify find_one was called with correct ID
        classification_repo.collection.find_one.assert_called_once_with({"_id": doc_id})

    async def test_get_by_id_not_found(
        self,
        classification_repo
    ):
        # Given: Classification doesn't exist
        doc_id = ObjectId()
        classification_repo.collection.find_one = AsyncMock(return_value=None)
        
        # When: Getting by ID
        result = await classification_repo.get_by_id(str(doc_id))
        
        # Then: Returns None
        assert result is None
        
        # Verify find_one was called
        classification_repo.collection.find_one.assert_called_once_with({"_id": doc_id})

    async def test_delete_success(
        self,
        classification_repo
    ):
        # Given: Classification exists
        doc_id = ObjectId()
        
        # Mock find_one to return existing doc
        classification_repo.collection.find_one = AsyncMock(
            return_value={"_id": doc_id}
        )
        
        # Mock delete_one to succeed
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        classification_repo.collection.delete_one = AsyncMock(
            return_value=mock_result
        )
        
        # When: Deleting classification
        result = await classification_repo.delete(str(doc_id))
        
        # Then: Returns True indicating success
        assert result is True
        
        # Verify operations were called
        classification_repo.collection.find_one.assert_called_once_with({"_id": doc_id})
        classification_repo.collection.delete_one.assert_called_once_with({"_id": doc_id})

    async def test_delete_not_found(
        self,
        classification_repo
    ):
        # Given: Classification doesn't exist
        doc_id = ObjectId()
        classification_repo.collection.find_one = AsyncMock(return_value=None)
        
        # When: Deleting classification
        result = await classification_repo.delete(str(doc_id))
        
        # Then: Returns False indicating not found
        assert result is False
        
        # Verify find_one was called
        classification_repo.collection.find_one.assert_called_once_with({"_id": doc_id})

    async def test_update_success(
        self,
        classification_repo
    ):
        # Given: Classification exists
        doc_id = ObjectId()
        now = datetime.now(UTC)
        updated_doc = {
            "_id": doc_id,
            "name": "Updated Test",
            "created_at": now,
            "updated_at": now
        }
        
        # Mock update_one to succeed
        mock_result = MagicMock()
        mock_result.modified_count = 1
        classification_repo.collection.update_one = AsyncMock(
            return_value=mock_result
        )
        
        # Mock find_one for get_by_id
        classification_repo.collection.find_one = AsyncMock(
            return_value=updated_doc
        )
        
        # When: Updating classification
        update_data = ClassificationCreate(name="Updated Test")
        result = await classification_repo.update(str(doc_id), update_data)
        
        # Then: Returns updated classification
        assert isinstance(result, Classification)
        assert result.name == "Updated Test"
        assert result.id == str(doc_id)
        
        # Verify operations were called
        classification_repo.collection.update_one.assert_called_once()
        classification_repo.collection.find_one.assert_called_once_with({"_id": doc_id})

    async def test_get_by_name_success(
        self,
        classification_repo
    ):
        # Given: Classification exists
        doc_id = ObjectId()
        now = datetime.now(UTC)
        mock_doc = {
            "_id": doc_id,
            "name": "Test",
            "created_at": now,
            "updated_at": now
        }
        
        # Mock find_one operation
        classification_repo.collection.find_one = AsyncMock(return_value=mock_doc)
        
        # When: Getting by name
        result = await classification_repo.get_by_name("Test")
        
        # Then: Returns correct classification
        assert isinstance(result, Classification)
        assert result.name == "Test"
        assert result.id == str(doc_id)
        
        # Verify find_one was called with correct name
        classification_repo.collection.find_one.assert_called_once_with({"name": "Test"}) 