"""Code review API endpoints."""
from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from src.database.database_utils import get_database
from src.models.code_review import CodeReview, CodeReviewCreate, ReviewStatus, CodeReviewList, PyObjectId
from src.models.classification import Classification
from src.utils.logging_utils import setup_logger
from src.agents.git_repos_agent import process_repositories
from src.agents.code_reviews_agent import check_compliance
from src.agents.standards_classification_agent import analyze_codebase_classifications
from src.utils.id_validation import ensure_object_id
from multiprocessing import Process
from datetime import timezone
import os
from src.repositories.code_review_repo import CodeReviewRepository
from src.api.dependencies import get_code_review_repo
import asyncio

UTC = timezone.utc
logger = setup_logger(__name__)

router = APIRouter()


async def get_classifications(db: AsyncIOMotorDatabase):
    """Get all classifications from database."""
    raw_classifications = await db.classifications.find().to_list(None)
    return [Classification.model_validate(doc) for doc in raw_classifications]


async def process_code_review(review_id: str, repository_url: str, standard_sets: list[str]):
    """Process a code review in the background."""
    try:
        db = await get_database()
        repo = CodeReviewRepository(db.code_reviews)

        # Update status to in progress
        await repo.update_status(review_id, ReviewStatus.IN_PROGRESS)

        # Process repository
        codebase_file = await process_repositories(repository_url)
        
        # Get all classifications
        raw_classifications = await db.classifications.find().to_list(None)
        classifications = [Classification.model_validate(doc) for doc in raw_classifications]
        
        # Analyze codebase to determine relevant classifications
        matching_classification_ids = await analyze_codebase_classifications(
            codebase_file.parent,
            classifications
        )
        
        # Get standards from database for each standard set
        compliance_reports = []
        for standard_set_id in standard_sets:
            try:
                # Get standard set from database
                standard_set = await db.standard_sets.find_one({"_id": ensure_object_id(standard_set_id)})
                if not standard_set:
                    logger.error(f"Standard set {standard_set_id} not found")
                    continue

                # Query for matching standards
                query = {
                    "standard_set_id": ensure_object_id(standard_set_id),
                    "$or": [
                        *[{"classification_ids": obj_id} for obj_id in matching_classification_ids],
                        {"$or": [
                            {"classification_ids": {"$size": 0}},
                            {"classification_ids": {"$exists": False}},
                            {"classification_ids": None}
                        ]}
                    ]
                }
                
                standards = await db.standards.find(query).to_list(None)
                if not standards:
                    logger.warning(f"No matching standards found for standard set {standard_set_id}")
                    continue

                # Check compliance
                report_file = await check_compliance(
                    codebase_file,
                    standards,
                    review_id,
                    standard_set.get("name", "Unknown"),
                    matching_classification_ids
                )

                # Create compliance report
                compliance_reports.append({
                    "_id": ObjectId(),
                    "standard_set_name": standard_set.get("name", "Unknown"),
                    "file": str(report_file),
                    "report": report_file.read_text()
                })

            except Exception as e:
                logger.error(f"Error processing standard set {standard_set_id}: {str(e)}")
                continue

        # Update the code review with compliance reports
        await repo.update_status(review_id, ReviewStatus.COMPLETED, compliance_reports)

    except Exception as e:
        logger.error(f"Error processing code review {review_id}: {str(e)}")
        db = await get_database()
        repo = CodeReviewRepository(db.code_reviews)
        await repo.update_status(review_id, ReviewStatus.FAILED)


def run_agent_process(review_id: str, repository_url: str, standard_sets: list[str]):
    """Run the agent process in a separate process."""
    async def _run():
        try:
            await process_code_review(review_id, repository_url, standard_sets)
        except Exception as e:
            logger.error(f"Error in agent process: {str(e)}", exc_info=True)

    asyncio.run(_run())


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
    repo: CodeReviewRepository = Depends(get_code_review_repo)
):
    """Create a new code review."""
    try:
        created_review = await repo.create(code_review)
        
        # Start agent in separate process
        Process(
            target=run_agent_process,
            args=(str(created_review.id), code_review.repository_url, code_review.standard_sets)
        ).start()

        return created_review
    except Exception as e:
        logger.error(f"Error creating code review: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating code review: {str(e)}"
        )


@router.get("/code-reviews",
        response_model=List[CodeReviewList],
        description="Get all code reviews",
        responses={
            200: {"description": "List of all code reviews"}
        })
async def get_code_reviews(
    repo: CodeReviewRepository = Depends(get_code_review_repo)
):
    """Get all code reviews."""
    try:
        return await repo.get_all()
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
    repo: CodeReviewRepository = Depends(get_code_review_repo)
):
    """Get a specific code review."""
    try:
        review = await repo.get_by_id(_id)
        if review is None:
            raise HTTPException(
                status_code=404,
                detail=f"Code review {_id} not found"
            )
        return review
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid review ID format: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching code review: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching code review: {str(e)}"
        )
