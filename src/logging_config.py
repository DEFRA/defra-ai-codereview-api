"""Logging configuration for the application."""
import logging
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

        # Console handler (INFO level)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(detailed_formatter)
        logger.addHandler(console_handler)

        # File handler (DEBUG level)
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Create a new log file for each run with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"code_review_{timestamp}.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger
