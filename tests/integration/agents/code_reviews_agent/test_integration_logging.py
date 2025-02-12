import logging
import pytest


def test_logging(caplog):
    # Setup logger for the code reviews agent
    logger = logging.getLogger('code_reviews_agent')
    logger.setLevel(logging.INFO)

    # Clear previous records in caplog
    caplog.clear()

    # Log an event that should be captured
    test_message = 'Code review event triggered'
    logger.info(test_message)

    # Assert that the log message is captured in the logs
    assert test_message in caplog.text, f"Expected log message '{test_message}' not found in logs: {caplog.text}"
