"""FastAPI dependency injection."""

from typing import AsyncGenerator
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from src.config import settings
from src.repositories.classification_repo import ClassificationRepository

async def get_classifications_collection() -> AsyncGenerator[AsyncIOMotorCollection, None]:
    """Get classifications collection."""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    try:
        yield client[settings.MONGO_INITDB_DATABASE].classifications
    finally:
        client.close()

async def get_repository(
    collection: AsyncIOMotorCollection = Depends(get_classifications_collection)
) -> ClassificationRepository:
    """Get repository instance."""
    return ClassificationRepository(collection)

async def get_database() -> AsyncGenerator:
    """Get database connection."""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    try:
        yield client[settings.MONGO_INITDB_DATABASE]
    finally:
        client.close() 