"""FastAPI dependency injection."""

from typing import AsyncGenerator
from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from src.config.config import settings
from src.repositories.classification_repo import ClassificationRepository
from src.repositories.standard_set_repo import StandardSetRepository
from src.repositories.code_review_repo import CodeReviewRepository
from src.services.code_review_service import CodeReviewService
from src.services.classification_service import ClassificationService
from src.services.standard_set_service import StandardSetService

async def get_db(request: Request) -> AsyncIOMotorDatabase:
    """Get database from app state."""
    return request.app.state.db

async def get_classifications_collection(
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> AsyncIOMotorCollection:
    """Get classifications collection."""
    return db.classifications

async def get_repository(
    collection: AsyncIOMotorCollection = Depends(get_classifications_collection)
) -> ClassificationRepository:
    """Get classification repository instance."""
    return ClassificationRepository(collection)

async def get_standard_sets_collection(
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> AsyncIOMotorCollection:
    """Get standard sets collection."""
    return db.standard_sets

async def get_standard_set_repo(
    collection: AsyncIOMotorCollection = Depends(get_standard_sets_collection)
) -> StandardSetRepository:
    """Get standard set repository instance."""
    return StandardSetRepository(collection)

async def get_code_reviews_collection(
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> AsyncIOMotorCollection:
    """Get code reviews collection."""
    return db.code_reviews

async def get_code_review_repo(
    collection: AsyncIOMotorCollection = Depends(get_code_reviews_collection)
) -> CodeReviewRepository:
    """Get code review repository instance."""
    return CodeReviewRepository(collection)

async def get_code_review_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    repo: CodeReviewRepository = Depends(get_code_review_repo)
) -> CodeReviewService:
    """Get code review service instance."""
    return CodeReviewService(db, repo)

async def get_classification_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    repo: ClassificationRepository = Depends(get_repository)
) -> ClassificationService:
    """Get classification service instance."""
    return ClassificationService(db, repo)

async def get_standard_set_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    repo: StandardSetRepository = Depends(get_standard_set_repo)
) -> StandardSetService:
    """Get standard set service instance."""
    return StandardSetService(db, repo) 