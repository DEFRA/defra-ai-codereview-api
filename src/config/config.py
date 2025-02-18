"""Configuration management for the application."""
from pydantic_settings import BaseSettings
from typing import Literal, List
from pydantic import ConfigDict, Field

class Settings(BaseSettings):
    """Application settings."""
    # Required API settings
    MONGO_URI: str
    ANTHROPIC_API_KEY: str
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    
    # Anthropic settings
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_MAX_TOKENS: int = 8192
    ANTHROPIC_TEMPERATURE: float = 0.0
    
    # Feature flags
    LLM_TESTING: bool = False
    LLM_TESTING_STANDARDS_FILES: str = ""
    
    # MongoDB Docker settings (optional with defaults)
    MONGO_INITDB_ROOT_USERNAME: str = "root"
    MONGO_INITDB_ROOT_PASSWORD: str = "example"
    MONGO_INITDB_DATABASE: str = "code_reviews"
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings() 