"""Service layer for classification operations."""
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.models.classification import Classification, ClassificationCreate
from src.repositories.classification_repo import ClassificationRepository
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)

class ClassificationService:
    """Service for managing classifications."""

    def __init__(self, db: AsyncIOMotorDatabase, repo: ClassificationRepository):
        """Initialize service with database and repository."""
        self.db = db
        self.repo = repo

    async def create_classification(self, classification: ClassificationCreate) -> Classification:
        """Create a new classification."""
        return await self.repo.create(classification)

    async def get_all_classifications(self) -> List[Classification]:
        """Get all classifications."""
        return await self.repo.get_all()

    async def delete_classification(self, id: str) -> bool:
        """Delete a classification."""
        return await self.repo.delete(id) 