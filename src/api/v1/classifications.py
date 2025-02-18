"""Classification API endpoints."""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from src.models.classification import Classification, ClassificationCreate
from src.services.classification_service import ClassificationService
from src.api.dependencies import get_classification_service
from src.utils.logging_utils import setup_logger
from src.utils.id_validation import ensure_object_id

logger = setup_logger(__name__)
router = APIRouter()

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
    service: ClassificationService = Depends(get_classification_service)
):
    """Create a new classification."""
    try:
        return await service.create_classification(classification)
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
    service: ClassificationService = Depends(get_classification_service)
):
    """Get all classifications."""
    try:
        return await service.get_all_classifications()
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
               404: {"description": "Classification not found"},
               400: {"description": "Invalid ObjectId format"}
           })
async def delete_classification(
    id: str,
    service: ClassificationService = Depends(get_classification_service)
):
    """Delete a classification."""
    try:
        ensure_object_id(id)
            
        success = await service.delete_classification(id)
        if success:
            return {"status": "success"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classification not found"
        )
    except ValueError as e:
        # Handle ObjectId validation errors from ensure_object_id
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting classification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete classification"
        ) 