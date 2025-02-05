"""Service layer for code review operations."""
from typing import List, Optional
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from multiprocessing import Process
from src.models.code_review import CodeReview, CodeReviewCreate, ReviewStatus, CodeReviewList
from src.models.classification import Classification
from src.repositories.code_review_repo import CodeReviewRepository
from src.agents.git_repos_agent import process_repositories
from src.agents.code_reviews_agent import check_compliance
from src.agents.standards_classification_agent import analyze_codebase_classifications
from src.utils.logging_utils import setup_logger
from src.utils.id_validation import ensure_object_id
from src.config.config import settings

logger = setup_logger(__name__)

def _run_in_process(review_id: str, repository_url: str, standard_sets: list[str]):
    """Run the review process in a separate process."""
    async def _run():
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client[settings.MONGO_INITDB_DATABASE]
        repo = CodeReviewRepository(db.code_reviews)

        try:
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
                    object_id = ensure_object_id(standard_set_id)
                    if not object_id:
                        logger.error(f"Invalid standard set ID format: {standard_set_id}")
                        continue
                        
                    standard_set = await db.standard_sets.find_one({"_id": object_id})
                    if not standard_set:
                        logger.error(f"Standard set {standard_set_id} not found")
                        continue

                    # Query for matching standards
                    query = {
                        "standard_set_id": object_id,
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
            await repo.update_status(review_id, ReviewStatus.FAILED)
        finally:
            client.close()

    try:
        asyncio.run(_run())
    except Exception as e:
        logger.error(f"Error in review process: {str(e)}")

class CodeReviewService:
    """Service for managing code reviews."""

    def __init__(self, db: AsyncIOMotorDatabase, repo: CodeReviewRepository):
        """Initialize service with database and repository."""
        self.db = db
        self.repo = repo

    async def create_review(self, code_review: CodeReviewCreate) -> CodeReview:
        """Create a new code review and start the review process."""
        # Validate standard sets exist before creating review
        for standard_set_id in code_review.standard_sets:
            object_id = ensure_object_id(standard_set_id)
            if not object_id:
                raise ValueError(f"Invalid standard set ID format: {standard_set_id}")
            
            standard_set = await self.db.standard_sets.find_one({"_id": object_id})
            if not standard_set:
                raise ValueError(f"Standard set {standard_set_id} not found")

        created_review = await self.repo.create(code_review)
        
        # Start agent in separate process
        Process(
            target=_run_in_process,
            args=(str(created_review.id), code_review.repository_url, code_review.standard_sets)
        ).start()

        return created_review

    async def get_all_reviews(self, status: Optional[ReviewStatus] = None) -> List[CodeReviewList]:
        """Get all code reviews.
        
        Args:
            status: Optional filter by review status
        """
        return await self.repo.get_all(status=status)

    async def get_review_by_id(self, review_id: str) -> CodeReview:
        """Get a specific code review."""
        return await self.repo.get_by_id(review_id) 