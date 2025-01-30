"""Logging configuration for the application."""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with both file and console handlers."""
    logger = logging.getLogger(name)

    # Only add handlers if the logger doesn't have any
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Console handler with configurable level
        console_level = os.getenv('CONSOLE_LOG_LEVEL', 'INFO')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_level.upper()))
        console_handler.setFormatter(detailed_formatter)
        logger.addHandler(console_handler)

        # File handler with configurable level (enabled by default)
        if os.getenv('ENABLE_FILE_LOGGING', 'true').lower() == 'true':
            logs_dir = Path(os.getenv('LOG_DIR', 'logs'))
            logs_dir.mkdir(exist_ok=True)

            # Create a new log file for each run with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = logs_dir / f"code_review_{timestamp}.log"

            file_level = os.getenv('FILE_LOG_LEVEL', 'DEBUG')
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, file_level.upper()))
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)

    return logger
