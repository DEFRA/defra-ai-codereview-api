"""MongoDB database initialization and schema validation."""
from datetime import datetime, UTC
from motor.motor_asyncio import AsyncIOMotorClient
from src.config import settings
from src.models.code_review import ReviewStatus

# MongoDB validation schemas
classifications_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name"],
        "properties": {
            "_id": {
                "bsonType": "objectId",
                "description": "Unique identifier"
            },
            "name": {
                "bsonType": "string",
                "description": "Classification name"
            }
        }
    }
}

standard_sets_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "repository_url"],
        "properties": {
            "_id": {
                "bsonType": "objectId",
                "description": "Unique identifier"
            },
            "name": {
                "bsonType": "string",
                "description": "Standard set name"
            },
            "repository_url": {
                "bsonType": "string",
                "description": "URL of the repository containing standards"
            },
            "custom_prompt": {
                "bsonType": "string",
                "description": "Custom prompt for LLM processing"
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

standards_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["text", "repository_path", "standard_set_id", "classification_ids", "created_at", "updated_at"],
        "properties": {
            "_id": {
                "bsonType": "objectId",
                "description": "Unique identifier"
            },
            "text": {
                "bsonType": "string",
                "description": "Standard text content"
            },
            "repository_path": {
                "bsonType": "string",
                "description": "Path to the standard in the repository"
            },
            "standard_set_id": {
                "bsonType": "objectId",
                "description": "Reference to the standard set"
            },
            "classification_ids": {
                "bsonType": "array",
                "items": {
                    "bsonType": "objectId",
                    "description": "Reference to classifications"
                },
                "description": "List of classification references"
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

    # Create collections with schema validation
    collections_config = {
        "code_reviews": code_review_schema,
        "classifications": classifications_schema,
        "standard_sets": standard_sets_schema,
        "standards": standards_schema
    }

    for collection_name, schema in collections_config.items():
        if collection_name not in await db.list_collection_names():
            await db.create_collection(
                collection_name,
                validator=schema
            )
        else:
            await db.command({
                "collMod": collection_name,
                "validator": schema
            })

    return db
