"""Logging configuration."""
import logging
import sys
from src.config import settings

def setup_logger(name: str) -> logging.Logger:
    """Configure and return a logger instance."""
    logger = logging.getLogger(name)
    
    # Set log level from environment variable
    logger.setLevel(settings.LOG_LEVEL)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)

    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    # Remove existing handlers to prevent duplicates
    logger.handlers.clear()
    
    logger.addHandler(console_handler)
    return logger 