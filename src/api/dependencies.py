"""FastAPI dependency injection."""

from typing import AsyncGenerator
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from src.config.config import settings
from src.repositories.classification_repo import ClassificationRepository
from src.repositories.standard_set_repo import StandardSetRepository
from src.repositories.code_review_repo import CodeReviewRepository
from src.services.code_review_service import CodeReviewService
from src.services.classification_service import ClassificationService
from src.database.database_utils import get_database

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

async def get_standard_sets_collection():
    """Get standard sets collection."""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    try:
        yield client[settings.MONGO_INITDB_DATABASE].standard_sets
    finally:
        client.close()

async def get_standard_set_repo(
    collection: AsyncIOMotorCollection = Depends(get_standard_sets_collection)
) -> StandardSetRepository:
    """Get standard set repository instance."""
    return StandardSetRepository(collection)

async def get_code_reviews_collection() -> AsyncGenerator[AsyncIOMotorCollection, None]:
    """Get code reviews collection."""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    try:
        yield client[settings.MONGO_INITDB_DATABASE].code_reviews
    finally:
        client.close()

async def get_code_review_repo(
    collection: AsyncIOMotorCollection = Depends(get_code_reviews_collection)
) -> CodeReviewRepository:
    """Get code review repository instance."""
    return CodeReviewRepository(collection)

async def get_code_review_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    repo: CodeReviewRepository = Depends(get_code_review_repo)
) -> CodeReviewService:
    """Get code review service instance."""
    return CodeReviewService(db, repo)

async def get_classification_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    repo: ClassificationRepository = Depends(get_repository)
) -> ClassificationService:
    """Get classification service instance."""
    return ClassificationService(db, repo) 