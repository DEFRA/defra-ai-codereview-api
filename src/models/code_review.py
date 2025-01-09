"""CodeReview model definition."""
from datetime import datetime, UTC
from enum import Enum
from typing import Optional, Any, ClassVar
from pydantic import BaseModel, Field, GetJsonSchemaHandler, ConfigDict
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema
from bson import ObjectId

class ReviewStatus(str, Enum):
    """Status of a code review."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"

class PyObjectId(str):
    """Custom type for handling MongoDB ObjectIds."""
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> CoreSchema:
        """Get Pydantic core schema."""
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(
                pattern="^[0-9a-fA-F]{24}$"
            ),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate)
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            )
        )

    @classmethod
    def validate(cls, value: Any) -> str:
        """Validate the ObjectId."""
        if not isinstance(value, (str, ObjectId)):
            raise ValueError("Invalid ObjectId")
        if isinstance(value, str) and not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return str(value)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: Any, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """Return the JSON Schema for this type."""
        return {"type": "string", "pattern": "^[0-9a-fA-F]{24}$"}

class CodeReviewCreate(BaseModel):
    """Input model for creating a code review."""
    repository_url: str

class CodeReview(BaseModel):
    """CodeReview model for responses."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias='_id')
    repository_url: str
    status: ReviewStatus = ReviewStatus.STARTED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
        arbitrary_types_allowed=True
    ) 