"""Unit tests for AnthropicClient utility."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from anthropic import AsyncAnthropic

from src.utils.anthropic_client import AnthropicClient
from src.config.config import settings

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Reset the singleton instance before each test."""
    AnthropicClient._instance = None
    yield

@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    mock_content = MagicMock()
    mock_content.text = "Test response"
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    return mock_message

@pytest.mark.asyncio
class TestAnthropicClient:
    """Test cases for AnthropicClient."""

    async def test_get_client_creates_new_instance(self):
        """Test client instance creation with valid API key."""
        # Given: No existing client instance
        assert AnthropicClient._instance is None

        # When: Getting client instance
        client = AnthropicClient.get_client()

        # Then: New instance is created
        assert isinstance(client, AsyncAnthropic)
        assert AnthropicClient._instance is client

    async def test_get_client_returns_existing_instance(self):
        """Test client instance reuse."""
        # Given: Existing client instance
        first_client = AnthropicClient.get_client()

        # When: Getting client instance again
        second_client = AnthropicClient.get_client()

        # Then: Same instance is returned
        assert first_client is second_client

    async def test_get_client_raises_error_without_api_key(self):
        """Test error handling when API key is missing."""
        # Given: No API key in settings
        with patch('src.utils.anthropic_client.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = None

            # When/Then: Getting client raises error
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY environment variable not set"):
                AnthropicClient.get_client()

    async def test_create_message_success(self, mock_anthropic_response):
        """Test successful message creation."""
        # Given: Mocked client instance
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=mock_anthropic_response)
        
        mock_client = AsyncMock()
        mock_client.messages = mock_messages
        
        with patch.object(AnthropicClient, 'get_client', return_value=mock_client):
            # When: Creating a message
            response = await AnthropicClient.create_message(
                prompt="Test prompt",
                system_prompt="Test system prompt"
            )

            # Then: Response is returned and client called correctly
            assert response == "Test response"
            mock_messages.create.assert_called_once_with(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=settings.ANTHROPIC_MAX_TOKENS,
                system="Test system prompt",
                temperature=settings.ANTHROPIC_TEMPERATURE,
                messages=[{"role": "user", "content": "Test prompt"}]
            )

    async def test_create_message_with_overrides(self, mock_anthropic_response):
        """Test message creation with parameter overrides."""
        # Given: Mocked client instance
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=mock_anthropic_response)
        
        mock_client = AsyncMock()
        mock_client.messages = mock_messages
        
        with patch.object(AnthropicClient, 'get_client', return_value=mock_client):
            # When: Creating message with overrides
            response = await AnthropicClient.create_message(
                prompt="Test prompt",
                system_prompt="Test system prompt",
                model="custom-model",
                max_tokens=100,
                temperature=0.8
            )

            # Then: Response is returned with overridden parameters
            assert response == "Test response"
            mock_messages.create.assert_called_once_with(
                model="custom-model",
                max_tokens=100,
                system="Test system prompt",
                temperature=0.8,
                messages=[{"role": "user", "content": "Test prompt"}]
            )

    async def test_create_message_handles_api_error(self):
        """Test error handling during message creation."""
        # Given: Mocked client that raises an error
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(side_effect=Exception("API Error"))
        
        mock_client = AsyncMock()
        mock_client.messages = mock_messages
        
        with patch.object(AnthropicClient, 'get_client', return_value=mock_client):
            # When/Then: Creating message raises error
            with pytest.raises(Exception, match="API Error"):
                await AnthropicClient.create_message(
                    prompt="Test prompt",
                    system_prompt="Test system prompt"
                ) 