"""Unit tests for the standards compliance checking functionality.

This module tests the core functionality for:
1. Generating prompts for compliance checking
2. Performing compliance checks against standards
3. Error handling for API and configuration issues
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from anthropic import AsyncAnthropic, AuthenticationError
from src.agents.code_reviews_agent import (
    generate_user_prompt,
    check_compliance,
    SYSTEM_PROMPT
)
import asyncio
from bson import ObjectId
from typing import Dict

# Test Constants
TEST_MONGODB_ID = "507f1f77bcf86cd799439011"
TEST_REVIEW_ID = "test_review_id"
TEST_STANDARD_SET = "test_standard_set"
TEST_API_KEY = "test_key"

# Common Instructions - used to make assertions more flexible
COMPLIANCE_INSTRUCTIONS = [
    "Compare the entire codebase",
    "Compare the codebase",
    "Analyze the codebase"
]


@pytest.fixture
def mock_standard_content() -> str:
    """
    Provide mock standard content for testing.

    Returns:
        str: A sample standards document with requirements
    """
    return """# Test Standard
## Requirements
- Requirement 1
- Requirement 2"""


@pytest.fixture
def mock_codebase_content() -> str:
    """
    Provide mock codebase content for testing.

    Returns:
        str: A sample Python file content
    """
    return """# File: test.py
def test():
    print("Hello World")"""


@pytest.fixture
def compliance_colors() -> Dict[str, str]:
    """
    Provide standard compliance color codes.

    Returns:
        Dict[str, str]: Mapping of compliance status to color codes
    """
    return {
        "yes": "#00703c",
        "no": "#d4351c",
        "partial": "#1d70b8"
    }


@pytest.fixture
def standard_id() -> str:
    """
    Provide standard test ID.

    Returns:
        str: Test standard identifier
    """
    return "test_standard"


@pytest.fixture
def mock_anthropic_error_client():
    """Provide mock Anthropic client that raises auth error."""
    error_response = {
        'type': 'error',
        'error': {
            'type': 'authentication_error',
            'message': 'invalid x-api-key'
        }
    }

    class MockMessages:
        async def create(self, *args, **kwargs):
            raise AuthenticationError(
                message=f"Error code: 401 - {error_response}",
                response=MagicMock(status_code=401),
                body=error_response
            )

    class MockAsyncAnthropic:
        def __init__(self, api_key):
            self.messages = MockMessages()

    return MockAsyncAnthropic


@pytest.fixture
def mock_anthropic_success_client():
    """Provide mock Anthropic client that returns success."""
    class MockMessages:
        async def create(self, *args, **kwargs):
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text="Test compliance report")]
            return mock_message

    class MockAsyncAnthropic:
        def __init__(self, api_key):
            self.messages = MockMessages()

    return MockAsyncAnthropic


@pytest.fixture
def mock_db_client():
    """Provide mock database client."""
    mock_db = MagicMock()
    mock_db.classifications.find.return_value.to_list = AsyncMock(return_value=[
        {"_id": ObjectId(TEST_MONGODB_ID), "name": "Test Classification"}
    ])
    return AsyncMock(return_value=mock_db)


@pytest.fixture
def mock_file_operations():
    """Provide mock file operations."""
    mock_read = MagicMock()
    mock_read.read.return_value = "Test content"
    mock_write = MagicMock()

    mock_open = MagicMock()
    mock_open.side_effect = [
        MagicMock(__enter__=MagicMock(return_value=mock_read)),
        MagicMock(__enter__=MagicMock(return_value=mock_write))
    ]

    return mock_open


@pytest.mark.prompt_generation
class TestPromptGeneration:
    """Tests for prompt generation functionality."""

    @pytest.mark.asyncio
    async def test_prompt_includes_required_components(
        self,
        mock_standard_content,
        mock_codebase_content,
        compliance_colors,
        standard_id
    ):
        """Test that generate_user_prompt includes all required components."""
        # Given
        standard = {"_id": standard_id, "text": mock_standard_content}

        # When
        prompt = await generate_user_prompt(standard, mock_codebase_content)

        # Then
        # 1. Standard header and content
        assert f"## Standard {standard_id}" in prompt
        assert mock_standard_content in prompt

        # 2. Codebase content
        assert mock_codebase_content in prompt

        # 3. Instructions - more flexible matching
        assert any(
            instruction in prompt for instruction in COMPLIANCE_INSTRUCTIONS)
        assert "Determine if the codebase" in prompt
        assert "files/sections" in prompt

        # 4. Report format - essential elements only
        assert "compliance report" in prompt
        assert "<span style=\"color:" in prompt
        assert "Recommendations" in prompt

        # 5. Color codes
        assert compliance_colors["yes"] in prompt
        assert compliance_colors["no"] in prompt
        assert compliance_colors["partial"] in prompt

    @pytest.mark.asyncio
    async def test_handles_empty_standard_content(self):
        """Test handling of empty standard content."""
        # Given
        standard = {"_id": "empty_standard", "text": ""}
        codebase = "print('test')"

        # When
        prompt = await generate_user_prompt(standard, codebase)

        # Then
        assert "## Standard empty_standard" in prompt
        assert any(
            instruction in prompt for instruction in COMPLIANCE_INSTRUCTIONS)

    @pytest.mark.parametrize("content_length", [100, 1000])
    @pytest.mark.asyncio
    async def test_handles_long_standard_content(self, content_length, mock_codebase_content):
        """Test handling of standards with different lengths."""
        # Given
        long_content = "# " + "very long standard " * content_length
        standard = {"_id": "long_standard", "text": long_content}

        # When
        prompt = await generate_user_prompt(standard, mock_codebase_content)

        # Then
        assert long_content in prompt
        assert mock_codebase_content in prompt
        assert any(
            instruction in prompt for instruction in COMPLIANCE_INSTRUCTIONS)


@pytest.mark.compliance_checking
class TestComplianceChecking:
    """Tests for compliance checking functionality."""

    @pytest.mark.asyncio
    async def test_handles_api_errors(
        self,
        mock_anthropic_error_client,
        mock_db_client,
        mock_file_operations
    ):
        """Test handling of API failures."""
        # Given
        codebase_file = Path("test_codebase.txt")
        standards = [{"_id": "test_standard", "text": "Test standard content"}]

        # When/Then
        with patch('src.agents.code_reviews_agent.AsyncAnthropic', mock_anthropic_error_client), \
                patch('builtins.open', create=True, new=mock_file_operations), \
                patch('src.database.get_database', mock_db_client), \
                patch.dict('os.environ', {'ANTHROPIC_API_KEY': TEST_API_KEY, 'LLM_TESTING': 'false'}):

            with pytest.raises(AuthenticationError) as exc_info:
                await check_compliance(
                    codebase_file,
                    standards,
                    TEST_REVIEW_ID,
                    TEST_STANDARD_SET,
                    [TEST_MONGODB_ID]
                )

            assert "invalid x-api-key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_error_without_api_key(
        self,
        mock_db_client,
        mock_file_operations
    ):
        """Test handling of missing API key."""
        # Given
        codebase_file = Path("test_codebase.txt")
        standards = [{"_id": "test_standard", "text": "Test standard content"}]

        # When/Then
        with patch.dict('os.environ', {'LLM_TESTING': 'false'}, clear=True), \
                patch('builtins.open', create=True, new=mock_file_operations), \
                patch('src.database.get_database', mock_db_client):

            with pytest.raises(ValueError) as exc_info:
                await check_compliance(
                    codebase_file,
                    standards,
                    TEST_REVIEW_ID,
                    TEST_STANDARD_SET,
                    [TEST_MONGODB_ID]
                )

            assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_successful_compliance_check(
        self,
        mock_anthropic_success_client,
        mock_db_client,
        mock_file_operations
    ):
        """Test successful compliance check and report generation."""
        # Given
        codebase_file = Path("test_codebase.txt")
        standards = [{"_id": "test_standard", "text": "Test standard content"}]

        # When
        with patch('src.agents.code_reviews_agent.AsyncAnthropic', mock_anthropic_success_client), \
                patch('builtins.open', create=True, new=mock_file_operations), \
                patch('src.database.get_database', mock_db_client), \
                patch('asyncio.sleep', AsyncMock()), \
                patch.dict('os.environ', {'ANTHROPIC_API_KEY': TEST_API_KEY, 'LLM_TESTING': 'false'}):

            report_file = await check_compliance(
                codebase_file,
                standards,
                TEST_REVIEW_ID,
                TEST_STANDARD_SET,
                [TEST_MONGODB_ID]
            )

            # Then
            expected_path = codebase_file.parent / \
                f"{TEST_REVIEW_ID}-{TEST_STANDARD_SET}.md"
            assert report_file == expected_path
            assert mock_file_operations.call_count == 2  # One read, one write
