"""Repository for classification database operations."""
from datetime import datetime, UTC
from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from src.models.classification import Classification, ClassificationCreate

class ClassificationRepository:
    """Repository for classification operations."""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        """Initialize repository with database collection."""
        self.collection = collection

    async def create(self, classification: ClassificationCreate) -> Classification:
        """Create a new classification."""
        now = datetime.now(UTC)
        doc = classification.model_dump()
        doc.update({
            "_id": ObjectId(),
            "created_at": now,
            "updated_at": now
        })
        
        result = await self.collection.insert_one(doc)
        return await self.get_by_id(str(result.inserted_id))

    async def get_by_id(self, id: str) -> Optional[Classification]:
        """Get a classification by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                return Classification.model_validate(doc)
            return None
        except Exception as e:
            # Log error here if needed
            return None

    async def get_all(self) -> List[Classification]:
        """Get all classifications ordered by name."""
        cursor = self.collection.find().sort("name", 1)
        classifications = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            classifications.append(Classification.model_validate(doc))
        return classifications

    async def delete(self, id: str) -> bool:
        """Delete a classification by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception as e:
            # Log error here if needed
            return False

    async def update(self, id: str, classification: ClassificationCreate) -> Optional[Classification]:
        """Update a classification."""
        try:
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
            # Log error here if needed
            return None 