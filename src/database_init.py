"""MongoDB database initialization and schema validation."""
from datetime import datetime, UTC
from motor.motor_asyncio import AsyncIOMotorClient
from src.config import settings
from src.models.code_review import ReviewStatus

# MongoDB validation schemas
code_review_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["repository_url", "status", "standard_sets", "created_at", "updated_at"],
        "properties": {
            "_id": {
                "bsonType": "objectId",
                "description": "Unique identifier"
            },
            "repository_url": {
                "bsonType": "string",
                "description": "Repository URL to analyze"
            },
            "status": {
                "enum": [s.value for s in ReviewStatus],
                "description": "Current review status"
            },
            "standard_sets": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["_id", "name"],
                    "properties": {
                        "_id": {
                            "bsonType": "objectId",
                            "description": "Standard set identifier"
                        },
                        "name": {
                            "bsonType": "string",
                            "description": "Name of the standard set"
                        }
                    }
                }
            },
            "compliance_reports": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["_id", "standard_set_name", "file", "report"],
                    "properties": {
                        "_id": {
                            "bsonType": "objectId",
                            "description": "Report identifier"
                        },
                        "standard_set_name": {
                            "bsonType": "string",
                            "description": "Name of the standard set"
                        },
                        "file": {
                            "bsonType": "string",
                            "description": "File path being reviewed"
                        },
                        "report": {
                            "bsonType": "string",
                            "description": "Detailed compliance report"
                        }
                    }
                }
            },
            "created_at": {
                "bsonType": "date",
                "description": "Creation timestamp"
            },
            "updated_at": {
                "bsonType": "date",
                "description": "Last update timestamp"
            }
        }
    }
}

async def init_database():
    """Initialize database with schema validation."""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.code_reviews

    # Create code_reviews collection with schema validation
    if "code_reviews" not in await db.list_collection_names():
        await db.create_collection(
            "code_reviews",
            validator=code_review_schema
        )
    else:
        await db.command({
            "collMod": "code_reviews",
            "validator": code_review_schema
        })

    return db
