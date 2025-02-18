"""Repository for code review database operations."""
from datetime import datetime, UTC
from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from src.models.code_review import CodeReview, CodeReviewCreate, ReviewStatus, CodeReviewList
from src.utils.logging_utils import setup_logger
from src.utils.id_validation import ensure_object_id

logger = setup_logger(__name__)

class CodeReviewRepository:
    """Repository for code review operations."""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        """Initialize repository with database collection."""
        self.collection = collection
        self.standard_sets_collection = collection.database.get_collection("standard_sets")

    async def create(self, code_review: CodeReviewCreate) -> CodeReview:
        """Create a new code review."""
        try:
            # Create initial document with properly formatted standard_sets
            standard_sets_info = []
            for set_id in code_review.standard_sets:
                object_id = ensure_object_id(set_id)
                if not object_id:
                    continue
                standard_set = await self.standard_sets_collection.find_one({"_id": object_id})
                if standard_set:
                    standard_sets_info.append({
                        "_id": object_id,
                        "name": standard_set["name"]
                    })

            now = datetime.now(UTC)
            doc = {
                "repository_url": code_review.repository_url,
                "standard_sets": standard_sets_info,
                "status": ReviewStatus.STARTED,
                "compliance_reports": [],
                "created_at": now,
                "updated_at": now
            }
            
            result = await self.collection.insert_one(doc)
            created_review = await self.collection.find_one({"_id": result.inserted_id})
            return CodeReview(**created_review)
        except Exception as e:
            logger.error(f"Error creating code review: {str(e)}")
            raise

    async def get_all(self, status: Optional[ReviewStatus] = None) -> List[CodeReviewList]:
        """Get all code reviews.
        
        Args:
            status: Optional filter by review status
        """
        try:
            # Build query based on status filter
            query = {}
            if status is not None:
                query["status"] = status
                
            reviews = await self.collection.find(query).sort("created_at", -1).to_list(None)
            valid_reviews = []
            
            for review in reviews:
                if review.get('_id') and str(review['_id']).strip():
                    review['_id'] = str(review['_id'])
                    standard_sets_info = await self._get_standard_sets_info(review.get('standard_sets', []))
                    review['standard_sets'] = standard_sets_info
                    valid_reviews.append(review)
                    
            return [CodeReviewList(**review) for review in valid_reviews]
        except Exception as e:
            logger.error(f"Error getting all code reviews: {str(e)}")
            raise

    async def get_by_id(self, id: str) -> Optional[CodeReview]:
        """Get a code review by ID."""
        try:
            object_id = ensure_object_id(id)
            if not object_id:
                return None
                
            review = await self.collection.find_one({"_id": object_id})
            
            if review:
                review['_id'] = str(review['_id'])
                standard_sets_info = await self._get_standard_sets_info(review.get('standard_sets', []))
                review['standard_sets'] = standard_sets_info
                return CodeReview(**review)
            return None
        except Exception as e:
            logger.error(f"Error getting code review by ID: {str(e)}")
            raise

    async def update_status(self, id: str, status: ReviewStatus, compliance_reports: list = None) -> bool:
        """Update code review status and optionally add compliance reports."""
        try:
            update_doc = {
                "status": status,
                "updated_at": datetime.now(UTC)
            }
            if compliance_reports is not None:
                update_doc["compliance_reports"] = compliance_reports
                
            result = await self.collection.update_one(
                {"_id": ensure_object_id(id)},
                {"$set": update_doc}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating code review status: {str(e)}")
            raise

    async def _get_standard_sets_info(self, standard_sets) -> List[dict]:
        """Helper method to get standard sets information."""
        standard_sets_info = []
        for standard_set in standard_sets:
            if isinstance(standard_set, dict) and '_id' in standard_set and 'name' in standard_set:
                standard_sets_info.append({
                    "id": str(standard_set['_id']),
                    "name": standard_set['name']
                })
            else:
                standard_set_id = standard_set
                object_id = ensure_object_id(standard_set_id)
                if not object_id:
                    continue
                
                standard_set_doc = await self.standard_sets_collection.find_one(
                    {"_id": object_id}
                )
                if standard_set_doc:
                    standard_sets_info.append({
                        "id": str(standard_set_doc['_id']),
                        "name": standard_set_doc.get('name', 'Unknown Standard Set')
                    })
                else:
                    standard_sets_info.append({
                        "id": str(standard_set_id),
                        "name": "Unknown Standard Set"
                    })
        return standard_sets_info 