"""Configuration management for the application."""
from pydantic_settings import BaseSettings
from typing import Literal
from pydantic import ConfigDict

class Settings(BaseSettings):
    """Application settings."""
    # Required API settings
    MONGO_URI: str
    ANTHROPIC_API_KEY: str
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    
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