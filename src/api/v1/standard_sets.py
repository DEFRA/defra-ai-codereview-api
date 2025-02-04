"""Standard sets API endpoints."""
from fastapi import APIRouter, HTTPException, Depends, status
from bson import ObjectId
from src.models.standard_set import StandardSet, StandardSetCreate, StandardSetWithStandards
from src.services.standard_set_service import StandardSetService
from src.api.dependencies import get_standard_set_service
from src.utils.logging_utils import setup_logger
from src.repositories.errors import DatabaseError, RepositoryError
from bson.errors import InvalidId
from src.utils.id_validation import ensure_object_id

logger = setup_logger(__name__)
router = APIRouter()

@router.post("/standard-sets", 
         response_model=StandardSet,
         status_code=status.HTTP_201_CREATED,
         description="Create a new standard set",
         responses={
             201: {"description": "Standard set created successfully"},
             400: {"description": "Invalid input"}
         })
async def create_standard_set(
    standard_set: StandardSetCreate,
    service: StandardSetService = Depends(get_standard_set_service)
) -> StandardSet:
    """Create a new standard set."""
    try:
        return await service.create_standard_set(standard_set)
    except RepositoryError as e:
        if "validation" in str(e).lower() or "invalid" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error creating standard set: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/standard-sets", response_model=list[StandardSet])
async def get_standard_sets(
    service: StandardSetService = Depends(get_standard_set_service)
):
    """Get all standard sets."""
    try:
        return await service.get_all_standard_sets()
    except DatabaseError as e:
        logger.error(f"Database error getting standard sets: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting standard sets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/standard-sets/{standard_set_id}", response_model=StandardSetWithStandards)
async def get_standard_set(
    standard_set_id: str,
    service: StandardSetService = Depends(get_standard_set_service)
) -> StandardSetWithStandards:
    """Get a standard set by ID."""
    try:
        try:
            object_id = ensure_object_id(standard_set_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        standard_set = await service.get_standard_set_by_id(standard_set_id)
        if not standard_set:
            raise HTTPException(status_code=404, detail="Standard set not found")
        return standard_set
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting standard set: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/standard-sets/{standard_set_id}", 
           description="Delete a standard set",
           responses={
               200: {"description": "Standard set deleted successfully"},
               404: {"description": "Standard set not found"},
               400: {"description": "Invalid ObjectId format"}
           })
async def delete_standard_set(
    standard_set_id: str,
    service: StandardSetService = Depends(get_standard_set_service)
) -> dict:
    """Delete a standard set and all its associated standards."""
    try:
        if not ensure_object_id(standard_set_id):
            raise HTTPException(status_code=400, detail="Invalid ObjectId format")
            
        success = await service.delete_standard_set(standard_set_id)
        if not success:
            raise HTTPException(status_code=404, detail="Standard set not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error deleting standard set: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting standard set: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 