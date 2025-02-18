"""Unit tests for Anthropic client utility."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from anthropic import AsyncAnthropic, AsyncAnthropicBedrock
from src.utils.anthropic_client import (
    AnthropicClient, 
    DirectAnthropicClient,
    BedrockAnthropicClient,
    USE_BEDROCK
)

from src.config.config import settings

@pytest.fixture
def mock_anthropic_response():
    """Create mock Anthropic response."""
    mock = MagicMock()
    mock.content = [MagicMock(text="Test response")]
    return mock

class TestAnthropicClient:
    """Test cases for AnthropicClient."""

    def setup_method(self):
        """Reset client instance before each test."""
        AnthropicClient._instance = None
        DirectAnthropicClient._instance = None
        BedrockAnthropicClient._instance = None

    async def test_get_client_creates_direct_instance(self):
        """Test direct client instance creation with valid API key."""
        # Given: No existing client instance and Bedrock disabled
        with patch('src.utils.anthropic_client.USE_BEDROCK', False):
            # When: Getting client instance
            client = AnthropicClient.get_client()

            # Then: New Direct instance is created
            assert isinstance(client, AsyncAnthropic)
            assert isinstance(AnthropicClient._instance, DirectAnthropicClient)

    async def test_get_client_creates_bedrock_instance(self):
        """Test bedrock client instance creation with valid credentials."""
        # Given: No existing client instance and Bedrock enabled
        with patch('src.utils.anthropic_client.USE_BEDROCK', True):
            with patch('src.utils.anthropic_client.settings') as mock_settings:
                mock_settings.AWS_ACCESS_KEY = "test-key"
                mock_settings.AWS_SECRET_KEY = "test-secret"
                mock_settings.AWS_REGION = "test-region"

                # When: Getting client instance
                client = AnthropicClient.get_client()

                # Then: New Bedrock instance is created
                assert isinstance(client, AsyncAnthropicBedrock)
                assert isinstance(AnthropicClient._instance, BedrockAnthropicClient)

    async def test_get_client_raises_error_without_credentials(self):
        """Test error handling when credentials are missing."""
        # Given: No credentials in settings
        with patch('src.utils.anthropic_client.USE_BEDROCK', True):
            with patch('src.utils.anthropic_client.settings') as mock_settings:
                mock_settings.AWS_ACCESS_KEY = None
                mock_settings.AWS_SECRET_KEY = None
                mock_settings.AWS_REGION = None

                # When/Then: Getting client raises error
                with pytest.raises(ValueError, match="AWS credentials .* must be set for Bedrock"):
                    AnthropicClient.get_client()

    async def test_direct_client_raises_error_without_api_key(self):
        """Test error handling when API key is missing for direct client."""
        # Given: No API key in settings
        with patch('src.utils.anthropic_client.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = None

            # When/Then: Getting client raises error
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY environment variable not set"):
                DirectAnthropicClient.get_client()

    async def test_create_message_with_direct_client(self, mock_anthropic_response):
        """Test message creation with direct client."""
        # Given: Mocked direct client instance
        with patch('src.utils.anthropic_client.USE_BEDROCK', False):
            mock_messages = AsyncMock()
            mock_messages.create = AsyncMock(return_value=mock_anthropic_response)

            mock_client = AsyncMock()
            mock_client.messages = mock_messages

            with patch.object(DirectAnthropicClient, 'get_client', return_value=mock_client):
                # When: Creating message
                response = await AnthropicClient.create_message(
                    prompt="Test prompt",
                    system_prompt="Test system prompt",
                    max_tokens=100,
                    temperature=0.8
                )

                # Then: Message is created with correct parameters
                assert response == "Test response"
                mock_messages.create.assert_called_once_with(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=100,
                    system="Test system prompt",
                    temperature=0.8,
                    messages=[{"role": "user", "content": "Test prompt"}]
                )

    async def test_create_message_with_bedrock_client(self, mock_anthropic_response):
        """Test message creation with bedrock client."""
        # Given: Mocked bedrock client instance
        with patch('src.utils.anthropic_client.USE_BEDROCK', True):
            mock_messages = AsyncMock()
            mock_messages.create = AsyncMock(return_value=mock_anthropic_response)

            mock_client = AsyncMock()
            mock_client.messages = mock_messages

            with patch.object(BedrockAnthropicClient, 'get_client', return_value=mock_client):
                with patch('src.utils.anthropic_client.settings') as mock_settings:
                    mock_settings.AWS_BEDROCK_MODEL = "test-bedrock-model"

                    # When: Creating message
                    response = await AnthropicClient.create_message(
                        prompt="Test prompt",
                        system_prompt="Test system prompt",
                        max_tokens=100,
                        temperature=0.8
                    )

                    # Then: Message is created with correct parameters
                    assert response == "Test response"
                    mock_messages.create.assert_called_once_with(
                        model="test-bedrock-model",
                        max_tokens=100,
                        system="Test system prompt",
                        temperature=0.8,
                        messages=[{"role": "user", "content": "Test prompt"}]
                    )

    async def test_create_message_handles_api_error(self, mock_anthropic_response):
        """Test error handling in message creation."""
        # Given: Mocked client that raises an error
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(side_effect=Exception("API Error"))

        mock_client = AsyncMock()
        mock_client.messages = mock_messages

        with patch.object(DirectAnthropicClient, 'get_client', return_value=mock_client):
            # When/Then: Creating message raises error
            with pytest.raises(Exception, match="API Error"):
                await AnthropicClient.create_message(
                    prompt="Test prompt",
                    system_prompt="Test system prompt"
                ) 