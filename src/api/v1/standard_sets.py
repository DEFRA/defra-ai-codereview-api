"""Standard sets API endpoints."""
from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from src.models.standard_set import StandardSet, StandardSetCreate, StandardSetWithStandards
from src.repositories.standard_set_repo import StandardSetRepository
from src.dependencies import (
    get_database,
    get_standard_sets_collection,
    get_standard_set_repo
)
from src.logging_config import setup_logger
from src.repositories.errors import DatabaseError, RepositoryError
from bson import ObjectId
from bson.errors import InvalidId

logger = setup_logger(__name__)

router = APIRouter(prefix="/standard-sets", tags=["standard-sets"])

@router.post("/", 
         response_model=StandardSet,
         status_code=status.HTTP_201_CREATED,
         description="Create a new standard set",
         responses={
             201: {"description": "Standard set created successfully"},
             400: {"description": "Invalid input"}
         })
async def create_standard_set(
    standard_set: StandardSetCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> dict:
    """Create a new standard set."""
    try:
        # Get the correct collection and pass it to repo
        collection = db.get_collection("standard_sets")
        repo = StandardSetRepository(collection)
        
        # First try to find if a standard set with this name already exists
        existing = await repo.find_by_name(standard_set.name)
        
        if existing:
            # If it exists, update it instead of creating new
            return await repo.update(standard_set)
        
        # If it doesn't exist, create new
        return await repo.create(standard_set)
    except RepositoryError as e:
        if "validation" in str(e).lower() or "invalid" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error creating standard set: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=list[StandardSet])
async def get_standard_sets(
    collection: AsyncIOMotorCollection = Depends(get_standard_sets_collection)
):
    """Get all standard sets."""
    try:
        cursor = collection.find({})
        standard_sets = await cursor.to_list(length=None)
        return standard_sets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.get("/{standard_set_id}", response_model=StandardSetWithStandards)
async def get_standard_set(
    standard_set_id: str,
    standard_set_repo: StandardSetRepository = Depends(get_standard_set_repo)
) -> StandardSetWithStandards:
    """Get a standard set by ID."""
    try:
        if not ObjectId.is_valid(standard_set_id):
            raise HTTPException(status_code=400, detail="Invalid ObjectId format")
            
        standard_set = await standard_set_repo.get_by_id(ObjectId(standard_set_id))
        if not standard_set:
            raise HTTPException(status_code=404, detail="Standard set not found")
        return standard_set
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting standard set: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{standard_set_id}", 
           description="Delete a standard set",
           responses={
               200: {"description": "Standard set deleted successfully"},
               404: {"description": "Standard set not found"},
               400: {"description": "Invalid ObjectId format"}
           })
async def delete_standard_set(
    standard_set_id: str,
    standard_set_repo: StandardSetRepository = Depends(get_standard_set_repo)
) -> dict:
    """Delete a standard set and all its associated standards."""
    # Validate ID format first, outside try-except
    if not ObjectId.is_valid(standard_set_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")
        
    try:
        success = await standard_set_repo.delete(ObjectId(standard_set_id))
        if not success:
            raise HTTPException(status_code=404, detail="Standard set not found")
        return {"status": "success"}
    except DatabaseError as e:
        logger.error(f"Database error deleting standard set: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException as e:
        # Re-raise HTTP exceptions directly
        raise e
    except Exception as e:
        logger.error(f"Unexpected error deleting standard set: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 