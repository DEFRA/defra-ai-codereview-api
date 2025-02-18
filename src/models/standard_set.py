"""Models for standard sets and standards."""
from datetime import datetime, UTC, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from src.models.code_review import PyObjectId
from src.models.standard import Standard

class StandardSetBase(BaseModel):
    """Base standard set model."""
    name: str = Field(..., description="Name of the standard set")
    repository_url: str = Field(..., description="URL of the repository containing standards")
    custom_prompt: str = Field(
        ..., 
        description="Custom prompt for LLM processing",
        max_length=1_000_000  # Allow up to 1 million characters
    )

class StandardSetCreate(BaseModel):
    """Standard set creation model."""
    name: str = Field(..., description="Name of the standard set")
    repository_url: str = Field(..., description="URL of the repository containing standards")
    custom_prompt: str = Field(
        ...,
        description="Custom prompt for LLM processing",
        max_length=1_000_000  # Allow up to 1 million characters
    )

class StandardSet(StandardSetBase):
    """Standard set model with ID and timestamps."""
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
                "name": "Security Standards",
                "repository_url": "https://github.com/org/security-standards",
                "custom_prompt": "Analyze code for security issues...",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    ) 

class StandardSetWithStandards(StandardSet):
    """Standard set model including associated standards."""
    standards: List[Standard] = [] 