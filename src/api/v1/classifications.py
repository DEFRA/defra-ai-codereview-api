"""Classification API endpoints."""
from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List
from bson.errors import InvalidId
from bson import ObjectId
from src.models.classification import Classification, ClassificationCreate
from src.repositories.classification_repo import ClassificationRepository
from src.dependencies import get_classifications_collection
from src.logging_config import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

async def get_repository(
    collection: AsyncIOMotorCollection = Depends(get_classifications_collection)
) -> ClassificationRepository:
    """Get classification repository instance."""
    return ClassificationRepository(collection)

@router.post("/classifications", 
         response_model=Classification,
         status_code=status.HTTP_201_CREATED,
         description="Create a new classification",
         responses={
             201: {"description": "Classification created successfully"},
             400: {"description": "Invalid input"}
         })
async def create_classification(
    classification: ClassificationCreate,
    repo: ClassificationRepository = Depends(get_repository)
):
    """Create a new classification."""
    try:
        return await repo.create(classification)
    except Exception as e:
        logger.error(f"Error creating classification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/classifications", 
        response_model=List[Classification],
        description="Get all classifications",
        responses={
            200: {"description": "List of all classifications"}
        })
async def list_classifications(
    repo: ClassificationRepository = Depends(get_repository)
):
    """Get all classifications."""
    try:
        return await repo.get_all()
    except Exception as e:
        logger.error(f"Error listing classifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve classifications"
        )

@router.delete("/classifications/{id}",
           description="Delete a classification",
           responses={
               200: {"description": "Classification deleted successfully"},
               400: {"description": "Invalid ObjectId format"}
           })
async def delete_classification(
    id: str,
    repo: ClassificationRepository = Depends(get_repository)
):
    """Delete a classification."""
    try:
        await repo.delete(id)
        return {"status": "success"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ObjectId format"
        )
    except Exception as e:
        logger.error(f"Error deleting classification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete classification"
        ) 