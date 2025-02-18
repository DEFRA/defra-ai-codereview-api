"""Service layer for standard set operations."""
from typing import List, Optional
from multiprocessing import Process
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.models.standard_set import StandardSet, StandardSetCreate, StandardSetWithStandards
from src.repositories.standard_set_repo import StandardSetRepository
from src.utils.logging_utils import setup_logger
from src.agents.standards_agent import process_standard_set

logger = setup_logger(__name__)

class StandardSetService:
    """Service for managing standard sets."""

    def __init__(self, db: AsyncIOMotorDatabase, repo: StandardSetRepository):
        """Initialize service with database and repository."""
        self.db = db
        self.repo = repo

    async def create_standard_set(self, standard_set: StandardSetCreate) -> StandardSet:
        """Create a new standard set."""
        # First try to find if a standard set with this name already exists
        existing = await self.repo.find_by_name(standard_set.name)
        
        if existing:
            # If it exists, update it instead of creating new
            standard_set_doc = await self.repo.update(standard_set)
        else:
            # If it doesn't exist, create new
            standard_set_doc = await self.repo.create(standard_set)
            
        # Start agent in separate process
        Process(
            target=self._run_agent_process_sync,
            args=(str(standard_set_doc.id), standard_set.repository_url)
        ).start()
        
        return standard_set_doc

    async def get_all_standard_sets(self) -> List[StandardSet]:
        """Get all standard sets."""
        return await self.repo.get_all()

    async def get_standard_set_by_id(self, id: str) -> Optional[StandardSetWithStandards]:
        """Get a specific standard set."""
        return await self.repo.get_by_id(id)

    async def delete_standard_set(self, id: str) -> bool:
        """Delete a standard set."""
        return await self.repo.delete(id)

    @staticmethod
    def _run_agent_process_sync(standard_set_id: str, repository_url: str):
        """Run the agent process synchronously."""
        import asyncio
        asyncio.run(process_standard_set(standard_set_id, repository_url)) 