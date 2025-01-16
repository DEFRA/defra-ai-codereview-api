"""Classification API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
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

@router.post("/classifications", response_model=Classification,
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
    return await repo.create(classification)

@router.get("/classifications", response_model=List[Classification],
        description="Get all classifications",
        responses={
            200: {"description": "List of all classifications"}
        })
async def list_classifications(
    repo: ClassificationRepository = Depends(get_repository)
):
    """Get all classifications."""
    return await repo.get_all()

@router.delete("/classifications/{id}",
           description="Delete a classification",
           responses={
               200: {"description": "Classification deleted successfully"},
               404: {"description": "Classification not found"},
               400: {"description": "Invalid classification ID format"}
           })
async def delete_classification(
    id: str,
    repo: ClassificationRepository = Depends(get_repository)
):
    """Delete a classification."""
    try:
        deleted = await repo.delete(id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Classification not found")
        return {"status": "success"}
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format") 