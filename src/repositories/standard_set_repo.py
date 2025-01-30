"""Repository for standard set database operations."""
from datetime import datetime, UTC, timezone
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from src.models.standard_set import StandardSet, StandardSetCreate, StandardSetWithStandards
from src.logging_config import setup_logger
from pymongo import ReturnDocument
from pymongo.errors import OperationFailure
from src.repositories.errors import DatabaseError, RepositoryError
from bson.errors import InvalidId

logger = setup_logger(__name__)

class StandardSetRepository:
    """Repository for standard set operations."""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        """Initialize repository with database collection."""
        self.collection = collection
        # Get standards collection from same database
        self.standards_collection = collection.database.get_collection("standards")
        
    async def create(self, standard_set: StandardSetCreate) -> StandardSet:
        """Create or update a standard set."""
        try:
            # First check if a standard set with this name exists
            existing = await self.collection.find_one({"name": standard_set.name})
            
            # If exists, delete associated standards first
            if existing:
                await self.standards_collection.delete_many(
                    {"standard_set_id": str(existing["_id"])}
                )
            
            # Prepare new document
            now = datetime.now(timezone.utc)
            doc = standard_set.model_dump()
            doc.update({
                "_id": ObjectId(),
                "created_at": now,
                "updated_at": now
            })
            
            # Replace/insert the standard set
            result = await self.collection.find_one_and_replace(
                {"name": standard_set.name},
                doc,
                return_document=ReturnDocument.AFTER,
                upsert=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
                return StandardSet(**result)
            
            doc["_id"] = str(doc["_id"])
            return StandardSet(**doc)
                
        except Exception as e:
            logger.error(f"Error creating standard set: {str(e)}")
            raise RepositoryError(f"Failed to create standard set: {str(e)}")

    async def get_all(self):
        """Get all standard sets."""
        standard_sets = []
        async for standard_set in self.collection.find():
            standard_sets.append(standard_set)
        return standard_sets 

    async def update(self, standard_set: StandardSetCreate) -> StandardSet:
        """Update an existing standard set."""
        try:
            # Find existing document to get its _id
            existing = await self.find_by_name(standard_set.name)
            if not existing:
                raise RepositoryError("Standard set not found")
            
            # Prepare update document
            now = datetime.now(UTC)
            update_doc = standard_set.model_dump()
            update_doc.update({
                "updated_at": now
            })
            
            # Keep the existing _id and created_at
            update_doc["_id"] = existing.id
            update_doc["created_at"] = existing.created_at
            
            # Update the document
            result = await self.collection.replace_one(
                {"_id": existing.id}, 
                update_doc
            )
            
            if result.modified_count == 0:
                raise RepositoryError("Failed to update standard set")
            
            return StandardSet(**update_doc)
        except Exception as e:
            logger.error(f"Error updating standard set: {str(e)}")
            raise RepositoryError(f"Error updating standard set: {str(e)}")

    async def find_by_name(self, name: str) -> Optional[StandardSet]:
        """Find a standard set by name."""
        try:
            doc = await self.collection.find_one({"name": name})
            if doc:
                return StandardSet(**doc)
            return None
        except Exception as e:
            logger.error(f"Error finding standard set by name: {e}")
            raise RepositoryError(f"Error finding standard set by name: {e}") 

    async def get_by_id(self, id: ObjectId) -> Optional[StandardSetWithStandards]:
        """Get a standard set by ID including its associated standards."""
        try:
            standard_set = await self.collection.find_one({"_id": id})
            if not standard_set:
                return None
            
            # Get associated standards
            standards = await self.standards_collection.find(
                {"standard_set_id": id}
            ).to_list(None)
            
            # Convert ObjectIds to strings in standards
            for standard in standards:
                standard["_id"] = str(standard["_id"])
                if "classification_ids" in standard:
                    standard["classification_ids"] = [str(id) for id in standard["classification_ids"]]
            
            # Convert ObjectId to string
            standard_set["_id"] = str(standard_set["_id"])
            
            # Create response object
            return StandardSetWithStandards(
                **standard_set,
                standards=standards
            )
        except Exception as e:
            logger.error(f"Error getting standard set by ID: {e}")
            raise RepositoryError(f"Error getting standard set by ID: {e}")

    async def delete(self, id: ObjectId) -> bool:
        """Delete a standard set and all its associated standards."""
        try:
            # Delete associated standards first
            await self.standards_collection.delete_many(
                {"standard_set_id": str(id)}
            )
            
            # Delete the standard set
            result = await self.collection.delete_one({"_id": id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting standard set: {e}")
            raise DatabaseError(f"Failed to delete standard set: {e}") 