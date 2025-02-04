"""Unit tests for StandardSetRepository."""
import pytest
from datetime import datetime, UTC
from bson import ObjectId
from unittest.mock import AsyncMock, MagicMock
from src.repositories.standard_set_repo import StandardSetRepository
from src.models.standard_set import StandardSetCreate, StandardSet, StandardSetWithStandards
from src.repositories.errors import DatabaseError, RepositoryError

@pytest.fixture
async def standard_set_repo():
    """Create a StandardSetRepository instance with mocked collection."""
    mock_collection = AsyncMock()
    mock_db = MagicMock()
    mock_standards_collection = AsyncMock()
    mock_db.get_collection.return_value = mock_standards_collection
    mock_collection.database = mock_db
    
    repo = StandardSetRepository(mock_collection)
    repo.standards_collection = mock_standards_collection
    return repo

class TestStandardSetRepository:
    """Tests for StandardSetRepository."""
    
    async def test_create_new_success(
        self,
        standard_set_repo
    ):
        # Given: No existing standard set
        doc_id = ObjectId()
        now = datetime.now(UTC)
        
        # Mock get_by_name to return None (no existing set)
        standard_set_repo.collection.find_one = AsyncMock(return_value=None)
        
        # Mock find_one_and_replace to succeed
        mock_doc = {
            '_id': doc_id,
            'name': 'Test Set',
            'repository_url': 'https://github.com/test/repo',
            'custom_prompt': 'Test prompt for standards',
            'created_at': now,
            'updated_at': now
        }
        standard_set_repo.collection.find_one_and_replace = AsyncMock(return_value=mock_doc)
        
        # When: Creating a new standard set
        result = await standard_set_repo.create(
            StandardSetCreate(
                name='Test Set',
                repository_url='https://github.com/test/repo',
                custom_prompt='Test prompt for standards'
            )
        )
        
        # Then: Returns created standard set
        assert isinstance(result, StandardSet)
        assert result.name == 'Test Set'
        assert result.repository_url == 'https://github.com/test/repo'
        assert result.custom_prompt == 'Test prompt for standards'
        assert isinstance(result.id, str)

    async def test_create_existing_replaces_success(
        self,
        standard_set_repo
    ):
        # Given: Existing standard set
        existing_id = ObjectId()
        now = datetime.now(UTC)
        
        # Mock find_one to return existing set
        existing_doc = {
            '_id': existing_id,
            'name': 'Test Set',
            'repository_url': 'https://github.com/test/repo',
            'custom_prompt': 'Original prompt',
            'created_at': now
        }
        standard_set_repo.collection.find_one = AsyncMock(return_value=existing_doc)
        
        # Mock delete_many for standards
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        standard_set_repo.standards_collection.delete_many = AsyncMock(return_value=mock_delete_result)
        
        # Mock find_one_and_replace for update
        updated_doc = {
            '_id': existing_id,
            'name': 'Test Set',
            'repository_url': 'https://github.com/test/repo',
            'custom_prompt': 'Updated prompt',
            'created_at': now,
            'updated_at': now
        }
        standard_set_repo.collection.find_one_and_replace = AsyncMock(return_value=updated_doc)
        
        # When: Creating with same name
        result = await standard_set_repo.create(
            StandardSetCreate(
                name='Test Set',
                repository_url='https://github.com/test/repo',
                custom_prompt='Updated prompt'
            )
        )
        
        # Then: Returns updated standard set
        assert isinstance(result, StandardSet)
        assert result.name == 'Test Set'
        assert result.repository_url == 'https://github.com/test/repo'
        assert result.custom_prompt == 'Updated prompt'
        assert result.id == str(existing_id)

    async def test_get_by_id_with_standards_success(
        self,
        standard_set_repo
    ):
        # Given: Existing standard set with standards
        set_id = ObjectId()
        now = datetime.now(UTC)
        
        # Mock find_one for standard set
        standard_set = {
            '_id': set_id,
            'name': 'Test Set',
            'repository_url': 'https://github.com/test/repo',
            'custom_prompt': 'Test prompt for standards',
            'created_at': now,
            'updated_at': now
        }
        standard_set_repo.collection.find_one = AsyncMock(return_value=standard_set)
        
        # Mock find for standards
        standards = [
            {
                '_id': ObjectId(),
                'text': f'Standard text {i}',
                'repository_path': f'/standards/standard_{i}.md',
                'standard_set_id': set_id,
                'classification_ids': [ObjectId(), ObjectId()],
                'created_at': now,
                'updated_at': now
            }
            for i in range(2)
        ]
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=standards)
        standard_set_repo.standards_collection.find = MagicMock(return_value=mock_cursor)
        
        # When: Getting standard set by ID
        result = await standard_set_repo.get_by_id(str(set_id))
        
        # Then: Returns standard set with standards
        assert isinstance(result, StandardSetWithStandards)
        assert result.name == 'Test Set'
        assert result.repository_url == 'https://github.com/test/repo'
        assert result.custom_prompt == 'Test prompt for standards'
        assert result.id == str(set_id)
        assert len(result.standards) == 2
        for i, standard in enumerate(result.standards):
            assert standard.text == f'Standard text {i}'
            assert standard.repository_path == f'/standards/standard_{i}.md'
            assert all(isinstance(id, str) for id in standard.classification_ids)

    async def test_delete_error_handling(
        self,
        standard_set_repo
    ):
        # Given: Database error occurs
        set_id = ObjectId()
        
        # Mock delete_many to raise error
        standard_set_repo.standards_collection.delete_many = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        # When/Then: Deleting fails gracefully
        with pytest.raises(DatabaseError) as exc_info:
            await standard_set_repo.delete(str(set_id))
        assert "Failed to delete standard set" in str(exc_info.value)

    async def test_update_success(
        self,
        standard_set_repo
    ):
        # Given: Existing standard set
        set_id = ObjectId()
        now = datetime.now(UTC)
        
        # Mock find_one for existing check
        existing = {
            '_id': set_id,
            'name': 'Test Set',
            'repository_url': 'https://github.com/test/repo',
            'custom_prompt': 'Original prompt',
            'created_at': now,
            'updated_at': now
        }
        standard_set_repo.collection.find_one = AsyncMock(return_value=existing)
        
        # Mock replace_one to succeed
        mock_result = MagicMock()
        mock_result.modified_count = 1
        standard_set_repo.collection.replace_one = AsyncMock(return_value=mock_result)
        
        # When: Updating standard set
        result = await standard_set_repo.update(
            StandardSetCreate(
                name='Test Set',
                repository_url='https://github.com/test/repo',
                custom_prompt='Updated prompt'
            )
        )
        
        # Then: Returns updated standard set
        assert isinstance(result, StandardSet)
        assert result.name == 'Test Set'
        assert result.repository_url == 'https://github.com/test/repo'
        assert result.custom_prompt == 'Updated prompt'
        assert str(result.id) == str(set_id)

    async def test_update_not_found(
        self,
        standard_set_repo
    ):
        # Given: Non-existent standard set
        
        # Mock find_one to return None
        standard_set_repo.collection.find_one = AsyncMock(return_value=None)
        
        # When/Then: Updating fails with error
        with pytest.raises(RepositoryError) as exc_info:
            await standard_set_repo.update(
                StandardSetCreate(
                    name='Test Set',
                    repository_url='https://github.com/test/repo',
                    custom_prompt='Updated prompt'
                )
            )
        assert "Standard set not found" in str(exc_info.value) 