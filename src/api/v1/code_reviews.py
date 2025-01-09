"""Code review API endpoints."""
from fastapi import APIRouter, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from src.models.code_review import CodeReview, CodeReviewCreate
from src.services.anthropic import AnthropicService
from src.database import get_database
from src.logging_config import setup_logger

logger = setup_logger(__name__)

router = APIRouter()
anthropic_service = AnthropicService()

@router.post("/code-reviews", response_model=CodeReview, status_code=status.HTTP_201_CREATED,
            description="Create a new code review",
            responses={
                201: {"description": "Code review created successfully"},
                400: {"description": "Invalid input"}
            })
async def create_code_review(code_review: CodeReviewCreate):
    """Create a new code review."""
    logger.info(f"Creating code review for repository: {code_review.repository_url}")
    try:
        db = await get_database()
        new_review = CodeReview(**code_review.dict())
        result = await db.code_reviews.insert_one(new_review.dict(by_alias=True))
        await anthropic_service.analyze_repository(code_review.repository_url)
        created_review = await db.code_reviews.find_one({"_id": result.inserted_id})
        logger.info(f"Created code review with ID: {result.inserted_id}")
        return CodeReview(**created_review)
    except Exception as e:
        logger.error(f"Error creating code review: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/code-reviews", response_model=List[CodeReview])
async def get_code_reviews():
    """Get all code reviews."""
    db = await get_database()
    reviews = await db.code_reviews.find().to_list(None)
    return [CodeReview(**review) for review in reviews]

@router.get("/code-reviews/{review_id}", response_model=CodeReview)
async def get_code_review(review_id: str):
    """Get a specific code review."""
    db = await get_database()
    if (review := await db.code_reviews.find_one({"_id": ObjectId(review_id)})) is not None:
        return CodeReview(**review)
    raise HTTPException(status_code=404, detail="Code review not found") 