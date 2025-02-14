"""Integration tests for the Code Reviews Agent."""
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

import pytest
from bson import ObjectId

from src.agents.code_reviews_agent import (
    CodeReviewConfig,
    check_compliance,
    CodeReviewError
)
from src.utils.anthropic_client import AnthropicClient
from src.database.database_utils import get_database

# Test Data
MOCK_STANDARD = {
    "_id": ObjectId(),
    "text": "Code should follow PEP 8 style guidelines",
    "repository_path": "test_repo/file.py"
}

MOCK_CODEBASE = """
def bad_function():
    x=1
    y=2
    return x+y
"""

EXPECTED_REPORT_CONTENT = """# Test Standard Set Code Review
Date: """


@pytest.fixture
async def mock_database():
    """Mock database for testing."""
    mock_db = AsyncMock()
    mock_db.classifications = AsyncMock()

    # Create a mock cursor with to_list method
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[{"name": "PEP 8"}])

    # Make find return the mock cursor
    mock_db.classifications.find = MagicMock(return_value=mock_cursor)

    # Create a mock get_database function
    async def mock_get_database():
        return mock_db

    with patch('src.agents.code_reviews_agent.get_database', new=mock_get_database):
        yield mock_db


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client responses."""
    with patch.object(AnthropicClient, 'create_message', new_callable=AsyncMock) as mock:
        mock.return_value = """## Standard: PEP 8 Style Guidelines

Compliant: <span style="color: #d4351c">**No**</span>

Relevant Files/Sections:
- test_repo/file.py

The code does not follow PEP 8 guidelines. Missing spaces around operators and no docstring.

## Specific Recommendations

- Add spaces around operators
- Add function docstring
"""
        yield mock


@pytest.fixture
def temp_codebase(tmp_path):
    """Create temporary codebase file."""
    codebase_file = tmp_path / "test_codebase.py"
    codebase_file.write_text(MOCK_CODEBASE)
    return codebase_file


@pytest.fixture(autouse=True)
async def setup_and_teardown():
    """Setup and teardown for each test."""
    # Setup - disable LLM testing by default
    os.environ["LLM_TESTING"] = "false"
    yield
    # Teardown
    if "LLM_TESTING" in os.environ:
        del os.environ["LLM_TESTING"]
    if "LLM_TESTING_STANDARDS_FILES" in os.environ:
        del os.environ["LLM_TESTING_STANDARDS_FILES"]

# Test Cases - Complete Code Review Flow


async def test_successful_code_review(
    mock_database,
    mock_anthropic,
    temp_codebase
):
    """Test successful end-to-end code review process."""
    # Given: A codebase and standards
    standards = [MOCK_STANDARD]
    review_id = "test_review"
    standard_set_name = "Test Standard Set"
    classification_ids = [str(ObjectId())]

    # When: Running a code review
    report_file = await check_compliance(
        codebase_file=temp_codebase,
        standards=standards,
        review_id=review_id,
        standard_set_name=standard_set_name,
        matching_classification_ids=classification_ids
    )

    # Then: Verify report was generated correctly
    assert report_file.exists()
    report_content = report_file.read_text()

    # Verify report structure
    assert standard_set_name in report_content
    assert "PEP 8" in report_content  # Classification name
    assert "Compliant: <span style=\"color: #d4351c\">**No**</span>" in report_content
    assert "test_repo/file.py" in report_content
    assert "Add spaces around operators" in report_content

    # Verify interactions
    mock_anthropic.assert_called_once()


async def test_code_review_with_llm_testing_enabled(
    mock_database,
    mock_anthropic,
    temp_codebase
):
    """Test code review with LLM testing mode enabled."""
    # Given: LLM testing enabled with specific test files
    os.environ["LLM_TESTING"] = "true"
    os.environ["LLM_TESTING_STANDARDS_FILES"] = "test_repo/file.py"

    standards = [
        MOCK_STANDARD,
        {
            "_id": ObjectId(),
            "text": "Should be filtered out",
            "repository_path": "other/path.py"
        }
    ]

    # When: Running a code review
    report_file = await check_compliance(
        codebase_file=temp_codebase,
        standards=standards,
        review_id="test_review",
        standard_set_name="Test Standard Set",
        matching_classification_ids=[str(ObjectId())]
    )

    # Then: Verify only matching standards were processed
    mock_anthropic.assert_called_once()  # Only one standard processed
    report_content = report_file.read_text()
    assert "Should be filtered out" not in report_content


async def test_code_review_with_invalid_codebase(
    mock_database,
    mock_anthropic
):
    """Test code review with non-existent codebase file."""
    # Given: A non-existent codebase file
    invalid_file = Path("nonexistent.py")

    # When/Then: Attempting code review should raise error
    with pytest.raises(CodeReviewError) as exc_info:
        await check_compliance(
            codebase_file=invalid_file,
            standards=[MOCK_STANDARD],
            review_id="test_review",
            standard_set_name="Test Standard Set",
            matching_classification_ids=[str(ObjectId())]
        )

    assert "Compliance check failed" in str(exc_info.value)
    mock_anthropic.assert_not_called()


async def test_code_review_with_anthropic_failure(
    mock_database,
    mock_anthropic,
    temp_codebase
):
    """Test code review when Anthropic API fails."""
    # Given: Anthropic API failure
    mock_anthropic.side_effect = Exception("API Error")

    # When/Then: Code review should handle error gracefully
    with pytest.raises(CodeReviewError) as exc_info:
        await check_compliance(
            codebase_file=temp_codebase,
            standards=[MOCK_STANDARD],
            review_id="test_review",
            standard_set_name="Test Standard Set",
            matching_classification_ids=[str(ObjectId())]
        )

    assert "Compliance check failed" in str(exc_info.value)
    assert "API Error" in str(exc_info.value)
    mock_anthropic.assert_called_once()


async def test_code_review_with_db_failure(
    mock_database,
    mock_anthropic,
    temp_codebase
):
    """Test code review when database operations fail."""
    # Given: Database failure at the fixture level
    mock_database.classifications.find.side_effect = Exception(
        "Database Error")

    # When/Then: Code review should handle error gracefully
    with pytest.raises(CodeReviewError) as exc_info:
        await check_compliance(
            codebase_file=temp_codebase,
            standards=[MOCK_STANDARD],
            review_id="test_review",
            standard_set_name="Test Standard Set",
            matching_classification_ids=[str(ObjectId())]
        )

    assert "Compliance check failed" in str(exc_info.value)
    assert "Database Error" in str(exc_info.value)
    mock_anthropic.assert_not_called()  # Should fail before reaching Anthropic API
