"""Classification model for managing technology/language classifications."""
from datetime import datetime, UTC
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from src.models.code_review import PyObjectId

class ClassificationBase(BaseModel):
    """Base classification model."""
    name: str = Field(..., description="Name of the classification (e.g. Python, Node.js)")

class ClassificationCreate(ClassificationBase):
    """Classification creation model."""
    pass

class Classification(ClassificationBase):
    """Classification model with ID and timestamps."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str},
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "Python",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    ) 