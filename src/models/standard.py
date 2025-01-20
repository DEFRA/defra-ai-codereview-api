"""Models for individual standards."""
from typing import List
from pydantic import BaseModel, Field
from src.models.code_review import PyObjectId

class Standard(BaseModel):
    """Model representing an individual standard."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    text: str = Field(..., description="Content of the standard")
    repository_path: str = Field(..., description="Path to the standard in the repository")
    standard_set_id: PyObjectId = Field(..., description="Reference to the parent standard set")
    classification_ids: List[PyObjectId] = Field(default_factory=list, description="References to associated classifications")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {PyObjectId: str},
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "text": "All functions must have type hints",
                "repository_path": "/python/type_hints.md",
                "standard_set_id": "507f1f77bcf86cd799439012",
                "classification_ids": ["507f1f77bcf86cd799439013"]
            }
        }
    } 