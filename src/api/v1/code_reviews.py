"""Code review API endpoints."""
from fastapi import APIRouter, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from src.models.code_review import CodeReview, CodeReviewCreate
from src.services.anthropic import AnthropicService
from src.database import get_database
from src.logging_config import setup_logger
from datetime import datetime

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
        # Create initial document without _id
        review_dict = {
            "repository_url": code_review.repository_url,
            "status": "started",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        logger.debug(f"Inserting review document: {review_dict}")
        result = await db.code_reviews.insert_one(review_dict)
        logger.debug(f"Insert result: {result.inserted_id}")
        
        # Fetch the created document
        created_review = await db.code_reviews.find_one({"_id": result.inserted_id})
        logger.debug(f"Created review document: {created_review}")
        
        # Start analysis in background
        await anthropic_service.analyze_repository(code_review.repository_url)
        
        logger.info(f"Successfully created code review with ID: {result.inserted_id}")
        return CodeReview(**created_review)
    except Exception as e:
        logger.error(f"Error creating code review: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating code review: {str(e)}")

@router.get("/code-reviews", response_model=List[CodeReview])
async def get_code_reviews():
    """Get all code reviews."""
    try:
        db = await get_database()
        logger.debug("Fetching all code reviews")
        reviews = await db.code_reviews.find().to_list(None)
        logger.debug(f"Found {len(reviews)} code reviews")
        
        # Filter out invalid documents and convert _id to string
        valid_reviews = []
        for review in reviews:
            if review.get('_id') and str(review['_id']).strip():  # Check for valid _id
                review['_id'] = str(review['_id'])
                valid_reviews.append(review)
            else:
                logger.warning(f"Skipping review with invalid _id: {review}")
            
        logger.debug(f"Processing {len(valid_reviews)} valid reviews")
        return [CodeReview(**review) for review in valid_reviews]
    except Exception as e:
        logger.error(f"Error fetching code reviews: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching code reviews: {str(e)}")

@router.get("/code-reviews/{_id}", response_model=CodeReview,
           responses={
               200: {"description": "Code review found"},
               404: {"description": "Code review not found"},
               400: {"description": "Invalid review ID format"}
           })
async def get_code_review(_id: str):
    """Get a specific code review."""
    try:
        if not ObjectId.is_valid(_id):
            raise ValueError("Invalid ObjectId format")
            
        db = await get_database()
        logger.debug(f"Database name: {db.name}")
        logger.debug(f"Collection name: {db.code_reviews.name}")
        
        # Log total count and first few documents
        total = await db.code_reviews.count_documents({})
        logger.debug(f"Total documents in collection: {total}")
        if total > 0:
            docs = await db.code_reviews.find().limit(5).to_list(None)
            logger.debug(f"Sample document IDs: {[str(doc['_id']) for doc in docs]}")
            # Log complete structure of matching document if it exists
            matching_doc = next((doc for doc in docs if str(doc['_id']) == _id), None)
            if matching_doc:
                logger.debug(f"Found matching document in sample: {matching_doc}")
                logger.debug(f"ID type in sample: {type(matching_doc['_id'])}")
        
        object_id = ObjectId(_id)
        logger.debug(f"Converted ID string '{_id}' to ObjectId: {object_id}")
        logger.debug(f"Querying database for _id: {object_id}")
        
        # Try direct ObjectId query first
        review = await db.code_reviews.find_one({"_id": object_id})
        if review is None:
            # Try string-based query as fallback
            logger.debug("ObjectId query failed, trying string-based query")
            review = await db.code_reviews.find_one({"_id": _id})
            
        logger.debug(f"Raw database response: {review}")
        
        if review is not None:
            logger.debug(f"Found review with ID: {_id}")
            return CodeReview(**review)
            
        logger.debug(f"No review found with ID: {_id}")
        raise HTTPException(status_code=404, detail="Code review not found")
    except ValueError as e:
        logger.error(f"Invalid ObjectId format: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid review ID format")
    except Exception as e:
        logger.error(f"Error retrieving code review: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Internal server error") 