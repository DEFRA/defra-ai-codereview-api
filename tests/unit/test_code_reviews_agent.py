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

@pytest.fixture
def mock_standard_content():
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
def mock_codebase_content():
    """
    Provide mock codebase content for testing.
    
    Returns:
        str: A sample Python file content
    """
    return """# File: test.py
def test():
    print("Hello World")"""

@pytest.mark.asyncio
async def test_generate_user_prompt_includes_required_components():
    """Test that generate_user_prompt includes all required components."""
    # Given
    standard = {"_id": "test_standard", "text": "Test standard content"}
    codebase_content = "print('Hello World')"

    # When
    prompt = await generate_user_prompt(standard, codebase_content)

    # Then
    assert "Test standard content" in prompt
    assert "print('Hello World')" in prompt
    assert "Standard test_standard" in prompt

@pytest.mark.asyncio
async def test_check_compliance_handles_api_errors():
    """
    Test handling of API failures.

    Given: API that raises an error
    When: Performing a compliance check
    Then: Should return error report with details
    """
    # Given
    codebase_file = Path("test_codebase.txt")
    standards = [{"_id": "test_standard", "text": "Test standard content"}]
    review_id = "test_review_id"
    standard_set_name = "test_standard_set"
    matching_classification_ids = ["507f1f77bcf86cd799439011"]  # Valid MongoDB ObjectId

    error_response = {
        'type': 'error',
        'error': {
            'type': 'authentication_error',
            'message': 'invalid x-api-key'
        }
    }

    # Create a mock client that raises AuthenticationError
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

    # Mock database operations
    mock_db = MagicMock()
    mock_db.classifications.find.return_value.to_list = AsyncMock(return_value=[
        {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "Test Classification"}
    ])
    mock_get_db = AsyncMock(return_value=mock_db)

    # When/Then
    with patch('src.agents.code_reviews_agent.AsyncAnthropic', MockAsyncAnthropic), \
         patch('builtins.open', create=True) as mock_open, \
         patch('src.database.get_database', mock_get_db), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key', 'LLM_TESTING': 'false'}):

        mock_open.return_value.__enter__.return_value.read.return_value = "Test content"
        with pytest.raises(AuthenticationError) as exc_info:
            await check_compliance(codebase_file, standards, review_id, standard_set_name, matching_classification_ids)

        assert "invalid x-api-key" in str(exc_info.value)

@pytest.mark.asyncio
async def test_check_compliance_raises_error_without_api_key():
    """
    Test handling of missing API key.

    Given: No API key in environment
    When: Attempting a compliance check
    Then: Should raise ValueError with clear message
    """
    # Given
    codebase_file = Path("test_codebase.txt")
    standards = [{"_id": "test_standard", "text": "Test standard content"}]
    review_id = "test_review_id"
    standard_set_name = "test_standard_set"
    matching_classification_ids = ["507f1f77bcf86cd799439011"]  # Valid MongoDB ObjectId

    # Mock database operations
    mock_db = MagicMock()
    mock_db.classifications.find.return_value.to_list = AsyncMock(return_value=[
        {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "Test Classification"}
    ])
    mock_get_db = AsyncMock(return_value=mock_db)

    # When/Then
    with patch.dict('os.environ', {'LLM_TESTING': 'false'}, clear=True), \
         patch('builtins.open', create=True) as mock_open, \
         patch('src.database.get_database', mock_get_db):
        mock_open.return_value.__enter__.return_value.read.return_value = "Test content"
        with pytest.raises(ValueError) as exc_info:
            await check_compliance(codebase_file, standards, review_id, standard_set_name, matching_classification_ids)

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

@pytest.mark.asyncio
async def test_check_compliance_successful():
    """
    Test successful compliance check with Claude.

    Given: Valid codebase and standards
    When: Performing a compliance check
    Then: Should generate and save report successfully
    """
    # Given
    codebase_file = Path("test_codebase.txt")
    standards = [{"_id": "test_standard", "text": "Test standard content"}]
    review_id = "test_review_id"
    standard_set_name = "test_standard_set"
    matching_classification_ids = ["507f1f77bcf86cd799439011"]  # Valid MongoDB ObjectId
    expected_report = "Test compliance report"

    # Create a properly mocked Anthropic client
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=expected_report)]

    class MockMessages:
        async def create(self, *args, **kwargs):
            return mock_message

    class MockAsyncAnthropic:
        def __init__(self, api_key):
            self.messages = MockMessages()

    # Mock database operations
    mock_db = MagicMock()
    mock_db.classifications.find.return_value.to_list = AsyncMock(return_value=[
        {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "Test Classification"}
    ])
    mock_get_db = AsyncMock(return_value=mock_db)

    # When/Then
    with patch('src.agents.code_reviews_agent.AsyncAnthropic', MockAsyncAnthropic), \
         patch('builtins.open', create=True) as mock_open, \
         patch('src.database.get_database', mock_get_db), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key', 'LLM_TESTING': 'false'}):

        # Mock both read and write file operations
        mock_read = MagicMock()
        mock_read.read.return_value = "Test content"
        mock_write = MagicMock()
        mock_open.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_read)),
            MagicMock(__enter__=MagicMock(return_value=mock_write))
        ]

        report_file = await check_compliance(codebase_file, standards, review_id, standard_set_name, matching_classification_ids)

        # Verify report was saved
        assert report_file == codebase_file.parent / f"{review_id}-{standard_set_name}.md"