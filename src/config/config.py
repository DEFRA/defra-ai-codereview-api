"""Configuration management for the application."""
from pydantic_settings import BaseSettings
from typing import Literal, List
from pydantic import ConfigDict, Field, field_validator, ValidationError

class Settings(BaseSettings):
    """Application settings."""
    # Required API settings
    MONGO_URI: str
    ANTHROPIC_API_KEY: str
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    
    # Anthropic settings
    ANTHROPIC_BEDROCK: str = "false"  # Controls whether to use AWS Bedrock or direct API
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_MAX_TOKENS: int = 8192
    ANTHROPIC_TEMPERATURE: float = 0.0
    
    # AWS Bedrock settings
    AWS_ACCESS_KEY: str = ""
    AWS_SECRET_KEY: str = ""
    AWS_REGION: str = ""
    AWS_BEDROCK_MODEL: str = ""
    
    # Feature flags
    LLM_TESTING: bool = False
    LLM_TESTING_STANDARDS_FILES: str = ""
    
    # MongoDB Docker settings (optional with defaults)
    MONGO_INITDB_ROOT_USERNAME: str = "root"
    MONGO_INITDB_ROOT_PASSWORD: str = "example"
    MONGO_INITDB_DATABASE: str = "code_reviews"
    
    @field_validator("AWS_ACCESS_KEY", "AWS_SECRET_KEY", "AWS_REGION", "AWS_BEDROCK_MODEL")
    @classmethod
    def validate_aws_settings(cls, v: str, info):
        """Validate AWS settings are provided when using Bedrock."""
        values = info.data
        if values.get("ANTHROPIC_BEDROCK", "").lower() == "true" and not v:
            raise ValueError(
                f"{info.field_name} must be set when ANTHROPIC_BEDROCK=true. "
                "Please check your .env file and ensure all AWS credentials are configured."
            )
        return v
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings() 