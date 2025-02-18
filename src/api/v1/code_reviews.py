"""Code review API endpoints."""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from src.models.code_review import (
    CodeReview,
    CodeReviewCreate,
    CodeReviewList,
    ReviewStatus
)
from src.utils.logging_utils import setup_logger
from src.services.code_review_service import CodeReviewService
from src.api.dependencies import get_code_review_service
from src.utils.id_validation import ensure_object_id

logger = setup_logger(__name__)
router = APIRouter()

@router.post("/code-reviews", 
         response_model=CodeReview,
         status_code=status.HTTP_201_CREATED,
         description="Create a new code review",
         responses={
             201: {"description": "Code review created successfully"},
             400: {"description": "Invalid input"}
         })
async def create_code_review(
    code_review: CodeReviewCreate,
    service: CodeReviewService = Depends(get_code_review_service)
) -> CodeReview:
    """Create a new code review."""
    try:
        return await service.create_review(code_review)
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Handle other errors
        logger.error(f"Error creating code review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating code review: {str(e)}"
        )

@router.get("/code-reviews",
        response_model=List[CodeReviewList],
        description="Get all code reviews",
        responses={
            200: {"description": "List of all code reviews"},
            422: {"description": "Invalid status value"}
        })
async def get_code_reviews(
    status: Optional[ReviewStatus] = None,
    service: CodeReviewService = Depends(get_code_review_service)
):
    """Get all code reviews.
    
    Args:
        status: Optional filter by review status
        service: Code review service dependency
    """
    try:
        return await service.get_all_reviews(status=status)
    except Exception as e:
        logger.error(f"Error fetching code reviews: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching code reviews: {str(e)}"
        )

@router.get("/code-reviews/{_id}",
        response_model=CodeReview,
        responses={
            200: {"description": "Code review found"},
            404: {"description": "Code review not found"},
            400: {"description": "Invalid review ID format"}
        })
async def get_code_review(
    _id: str,
    service: CodeReviewService = Depends(get_code_review_service)
):
    """Get a specific code review."""
    try:
        ensure_object_id(_id)
            
        review = await service.get_review_by_id(_id)
        if review is None:
            raise HTTPException(
                status_code=404,
                detail=f"Code review {_id} not found"
            )
        return review
    except ValueError as e:
        # Handle ObjectId validation errors from ensure_object_id
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching code review: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching code review: {str(e)}"
        )
