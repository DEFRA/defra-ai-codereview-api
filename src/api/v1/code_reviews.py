"""Code review API endpoints."""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from src.database import get_database
from src.models.code_review import CodeReview, CodeReviewCreate, ReviewStatus
from src.logging_config import setup_logger
from src.agents.git_repos_agent import process_repositories
from src.agents.code_reviews_agent import check_compliance
from multiprocessing import Process
from datetime import timezone
import os

UTC = timezone.utc
logger = setup_logger(__name__)

router = APIRouter()


async def process_code_review(review_id: str, repository_url: str, standard_sets: list[str]):
    """Process a code review in the background."""
    try:
        db = await get_database()

        # Update status to in progress
        await db.code_reviews.update_one(
            {"_id": ObjectId(review_id)},
            {"$set": {
                "status": ReviewStatus.IN_PROGRESS,
                "updated_at": datetime.now(UTC)
            }}
        )

        # Process repository
        codebase_file = await process_repositories(repository_url)
        
        # Get standards from database for each standard set
        compliance_reports = {}
        for standard_set_id in standard_sets:
            try:
                # Get standard set from database
                standard_set = await db.standard_sets.find_one({"_id": ObjectId(standard_set_id)})
                if not standard_set:
                    logger.error(f"Standard set {standard_set_id} not found")
                    continue
                
                # Get standards for this set
                standards = await db.standards.find({"standard_set_id": standard_set_id}).to_list(None)
                if not standards:
                    logger.error(f"No standards found for standard set {standard_set_id}")
                    continue

                # Check compliance
                report_file = await check_compliance(codebase_file, standards, review_id, standard_set["name"])
                compliance_reports[standard_set_id] = str(report_file)

            except Exception as e:
                logger.error(f"Error processing standard set {standard_set_id}: {str(e)}")
                continue

        # Update review with results
        await db.code_reviews.update_one(
            {"_id": ObjectId(review_id)},
            {"$set": {
                "status": ReviewStatus.COMPLETED,
                "compliance_reports": compliance_reports,
                "updated_at": datetime.now(UTC)
            }}
        )

    except Exception as e:
        logger.error(f"Error processing code review {review_id}: {str(e)}")
        await db.code_reviews.update_one(
            {"_id": ObjectId(review_id)},
            {"$set": {
                "status": ReviewStatus.FAILED,
                "updated_at": datetime.now(UTC)
            }}
        )


def run_agent_process(review_id: str, repository_url: str, standard_sets: list[str]):
    """Run the agent process in a separate process."""
    import asyncio

    async def _run():
        try:
            db = await get_database()
            await process_code_review(review_id, repository_url, standard_sets)
        except Exception as e:
            logger.error(f"Error in agent process: {str(e)}", exc_info=True)

    asyncio.run(_run())


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
        # Create initial document
        review_dict = {
            "repository_url": code_review.repository_url,
            "standard_sets": code_review.standard_sets,
            "status": ReviewStatus.STARTED,
            "compliance_reports": {},
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        logger.debug(f"Inserting review document: {review_dict}")
        result = await db.code_reviews.insert_one(review_dict)
        logger.debug(f"Insert result: {result.inserted_id}")

        # Start agent in separate process
        Process(
            target=run_agent_process,
            args=(str(result.inserted_id), code_review.repository_url, code_review.standard_sets)
        ).start()

        # Fetch the created document
        created_review = await db.code_reviews.find_one({"_id": result.inserted_id})
        logger.debug(f"Created review document: {created_review}")

        logger.info(f"Successfully created code review with ID: {result.inserted_id}")
        return CodeReview(**created_review)
    except Exception as e:
        logger.error(f"Error creating code review: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error creating code review: {str(e)}")


@router.get("/code-reviews", response_model=List[CodeReview])
async def get_code_reviews():
    """Get all code reviews."""
    try:
        db = await get_database()
        logger.debug("Fetching all code reviews")
        reviews = await db.code_reviews.find().sort("updated_at", -1).to_list(None)
        logger.debug(f"Found {len(reviews)} code reviews")

        # Filter out invalid documents and convert _id to string
        valid_reviews = []
        for review in reviews:
            # Check for valid _id
            if review.get('_id') and str(review['_id']).strip():
                review['_id'] = str(review['_id'])
                valid_reviews.append(review)
            else:
                logger.warning(f"Skipping review with invalid _id: {review}")

        logger.debug(f"Processing {len(valid_reviews)} valid reviews")
        return [CodeReview(**review) for review in valid_reviews]
    except Exception as e:
        logger.error(f"Error fetching code reviews: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching code reviews: {str(e)}")


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
            matching_doc = next(
                (doc for doc in docs if str(doc['_id']) == _id), None)
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
