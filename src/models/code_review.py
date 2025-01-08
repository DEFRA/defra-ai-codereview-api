"""CodeReview model definition."""
from datetime import datetime
from enum import Enum
from typing import Optional, Any, ClassVar
from pydantic import BaseModel, Field, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from bson import ObjectId

class ReviewStatus(str, Enum):
    """Status of a code review."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"

class PyObjectId(str):
    """Custom type for handling MongoDB ObjectIds."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: Any, *args, **kwargs) -> str:
        if not isinstance(value, (str, ObjectId)):
            raise ValueError("Invalid ObjectId")
        if isinstance(value, str) and not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return str(ObjectId(value))

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: Any, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """Return the JSON Schema for this type."""
        return {"type": "string", "pattern": "^[0-9a-fA-F]{24}$"}

class CodeReview(BaseModel):
    """CodeReview model."""
    id: Optional[PyObjectId] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    repository_url: str
    status: ReviewStatus = ReviewStatus.STARTED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic config."""
        json_encoders = {ObjectId: str}
        populate_by_name = True 