"""Repository for classification database operations."""
from datetime import datetime, UTC
from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from src.models.classification import Classification, ClassificationCreate
from src.logging_config import setup_logger

logger = setup_logger(__name__)

class ClassificationRepository:
    """Repository for classification operations."""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        """Initialize repository with database collection."""
        self.collection = collection

    async def create(self, classification: ClassificationCreate) -> Classification:
        """Create a new classification."""
        try:
            # Check if classification with same name exists
            existing = await self.get_by_name(classification.name)
            if existing:
                raise ValueError(f"Classification with name '{classification.name}' already exists")

            now = datetime.now(UTC)
            doc = classification.model_dump()
            doc.update({
                "_id": ObjectId(),
                "created_at": now,
                "updated_at": now
            })
            
            await self.collection.insert_one(doc)
            doc["_id"] = str(doc["_id"])
            return Classification.model_validate(doc)
        except Exception as e:
            logger.error(f"Error creating classification: {str(e)}")
            raise

    async def get_by_id(self, id: str) -> Optional[Classification]:
        """Get a classification by ID."""
        try:
            if not ObjectId.is_valid(id):
                return None
                
            doc = await self.collection.find_one({"_id": ObjectId(id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                return Classification.model_validate(doc)
            return None
        except Exception as e:
            logger.error(f"Error getting classification by ID: {str(e)}")
            return None

    async def get_all(self) -> List[Classification]:
        """Get all classifications."""
        try:
            cursor = self.collection.find()
            classifications = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                try:
                    classifications.append(Classification.model_validate(doc))
                except Exception as e:
                    logger.warning(f"Skipping invalid classification document: {str(e)}")
            return classifications
        except Exception as e:
            logger.error(f"Error getting all classifications: {str(e)}")
            raise

    async def delete(self, id: str) -> bool:
        """Delete a classification by ID."""
        try:
            if not ObjectId.is_valid(id):
                raise ValueError("Invalid ObjectId format")
            
            # Check if document exists first
            doc = await self.collection.find_one({"_id": ObjectId(id)})
            if not doc:
                return False
                
            result = await self.collection.delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except ValueError as e:
            logger.error(f"Invalid ID format: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error deleting classification: {str(e)}")
            return False

    async def update(self, id: str, classification: ClassificationCreate) -> Optional[Classification]:
        """Update a classification."""
        try:
            if not ObjectId.is_valid(id):
                return None
                
            update_data = classification.model_dump()
            update_data["updated_at"] = datetime.now(UTC)
            
            result = await self.collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                return await self.get_by_id(id)
            return None
        except Exception as e:
            logger.error(f"Error updating classification: {str(e)}")
            return None

    async def get_by_name(self, name: str) -> Optional[Classification]:
        """Get a classification by name."""
        try:
            doc = await self.collection.find_one({"name": name})
            if doc:
                doc["_id"] = str(doc["_id"])
                return Classification.model_validate(doc)
            return None
        except Exception as e:
            logger.error(f"Error getting classification by name: {str(e)}")
            return None 