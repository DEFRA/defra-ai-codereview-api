"""Unit tests for CodeReviewRepository."""
import pytest
from datetime import datetime, UTC
from bson import ObjectId
from unittest.mock import AsyncMock, MagicMock
from src.repositories.code_review_repo import CodeReviewRepository
from src.models.code_review import CodeReviewCreate, CodeReview, CodeReviewList, ReviewStatus
from src.repositories.errors import DatabaseError, RepositoryError

@pytest.fixture
def code_review_repo():
    """Create a CodeReviewRepository instance with mocked collection."""
    mock_collection = AsyncMock()
    mock_db = MagicMock()
    mock_standard_sets_collection = AsyncMock()
    mock_db.get_collection.return_value = mock_standard_sets_collection
    mock_collection.database = mock_db
    
    repo = CodeReviewRepository(mock_collection)
    repo.standard_sets_collection = mock_standard_sets_collection
    return repo

class TestCodeReviewRepository:
    """Tests for CodeReviewRepository."""
    
    async def test_create_success(
        self,
        code_review_repo
    ):
        # Given: New code review data
        doc_id = ObjectId()
        now = datetime.now(UTC)
        standard_set_id = str(ObjectId())
        
        # Mock standard set lookup
        standard_set = {
            "_id": ObjectId(standard_set_id),
            "name": "Test Standard Set"
        }
        code_review_repo.standard_sets_collection.find_one = AsyncMock(return_value=standard_set)
        
        # Mock insert_one to succeed
        mock_result = MagicMock()
        mock_result.inserted_id = doc_id
        code_review_repo.collection.insert_one = AsyncMock(return_value=mock_result)
        
        # Mock find_one for get_by_id
        mock_doc = {
            '_id': doc_id,
            'repository_url': 'https://github.com/test/repo',
            'standard_sets': [{
                '_id': ObjectId(standard_set_id),
                'name': 'Test Standard Set'
            }],
            'status': ReviewStatus.STARTED.value,
            'compliance_reports': [],
            'created_at': now,
            'updated_at': now
        }
        code_review_repo.collection.find_one = AsyncMock(return_value=mock_doc)
        
        # When: Creating a new code review
        result = await code_review_repo.create(
            CodeReviewCreate(
                repository_url='https://github.com/test/repo',
                standard_sets=[standard_set_id]
            )
        )
        
        # Then: Returns created code review
        assert isinstance(result, CodeReview)
        assert result.repository_url == 'https://github.com/test/repo'
        assert len(result.standard_sets) == 1
        assert str(result.standard_sets[0].id) == standard_set_id
        assert result.status == ReviewStatus.STARTED
        assert isinstance(result.id, ObjectId)

    async def test_create_handles_error(
        self,
        code_review_repo
    ):
        # Given: Database error occurs
        standard_set_id = str(ObjectId())
        
        # Mock standard set lookup
        standard_set = {
            "_id": ObjectId(standard_set_id),
            "name": "Test Standard Set"
        }
        code_review_repo.standard_sets_collection.find_one = AsyncMock(return_value=standard_set)
        
        # Mock insert_one to fail
        code_review_repo.collection.insert_one = AsyncMock(
            side_effect=DatabaseError("Failed to create code review")
        )
        
        # When/Then: Creating fails gracefully
        with pytest.raises(DatabaseError) as exc_info:
            await code_review_repo.create(
                CodeReviewCreate(
                    repository_url='https://github.com/test/repo',
                    standard_sets=[standard_set_id]
                )
            )
        assert "Failed to create code review" in str(exc_info.value)

    async def test_get_all_success(
        self,
        code_review_repo
    ):
        # Given: Existing code reviews
        now = datetime.now(UTC)
        mock_docs = [
            {
                '_id': ObjectId(),
                'repository_url': f'https://github.com/test/repo{i}',
                'standard_sets': [{
                    '_id': ObjectId(),
                    'name': f'Standard Set {i}'
                }],
                'status': ReviewStatus.STARTED.value,
                'compliance_reports': [],
                'created_at': now,
                'updated_at': now
            }
            for i in range(2)
        ]
        
        # Mock find operation with cursor
        mock_cursor = AsyncMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=mock_docs)
        code_review_repo.collection.find = MagicMock(return_value=mock_cursor)
        
        # When: Getting all code reviews
        result = await code_review_repo.get_all()
        
        # Then: Returns list of code reviews
        assert len(result) == 2
        for i, review in enumerate(result):
            assert isinstance(review, CodeReviewList)
            assert review.repository_url == f'https://github.com/test/repo{i}'
            assert review.status == ReviewStatus.STARTED

    async def test_get_by_id_success(
        self,
        code_review_repo
    ):
        # Given: Existing code review
        review_id = ObjectId()
        now = datetime.now(UTC)
        standard_set_id = str(ObjectId())
        
        # Mock find_one operation
        mock_doc = {
            '_id': review_id,
            'repository_url': 'https://github.com/test/repo',
            'standard_sets': [{
                '_id': ObjectId(standard_set_id),
                'name': 'Test Standard Set'
            }],
            'status': ReviewStatus.STARTED.value,
            'compliance_reports': [],
            'created_at': now,
            'updated_at': now
        }
        code_review_repo.collection.find_one = AsyncMock(return_value=mock_doc)
        
        # When: Getting code review by ID
        result = await code_review_repo.get_by_id(str(review_id))
        
        # Then: Returns code review
        assert isinstance(result, CodeReview)
        assert result.id == str(review_id)
        assert result.repository_url == 'https://github.com/test/repo'
        assert len(result.standard_sets) == 1
        assert result.status == ReviewStatus.STARTED

    async def test_get_by_id_not_found(
        self,
        code_review_repo
    ):
        # Given: Non-existent code review
        review_id = ObjectId()
        
        # Mock find_one to return None
        code_review_repo.collection.find_one = AsyncMock(return_value=None)
        
        # When: Getting non-existent code review
        result = await code_review_repo.get_by_id(str(review_id))
        
        # Then: Returns None
        assert result is None

    async def test_update_status_success(
        self,
        code_review_repo
    ):
        # Given: Existing code review
        review_id = ObjectId()
        
        # Mock update_one operation
        mock_result = MagicMock()
        mock_result.modified_count = 1
        code_review_repo.collection.update_one = AsyncMock(return_value=mock_result)
        
        # When: Updating status
        result = await code_review_repo.update_status(
            str(review_id),
            ReviewStatus.COMPLETED
        )
        
        # Then: Returns True indicating success
        assert result is True

    async def test_update_status_not_found(
        self,
        code_review_repo
    ):
        # Given: Non-existent code review
        review_id = ObjectId()
        
        # Mock update_one to indicate no document was updated
        mock_result = MagicMock()
        mock_result.modified_count = 0
        code_review_repo.collection.update_one = AsyncMock(return_value=mock_result)
        
        # When: Updating non-existent review
        result = await code_review_repo.update_status(
            str(review_id),
            ReviewStatus.COMPLETED
        )
        
        # Then: Returns False indicating failure
        assert result is False 