"""Singleton Anthropic client utility."""
import os
from abc import ABC, abstractmethod
from typing import Optional, Protocol, Union, Any
from anthropic import AsyncAnthropic, AsyncAnthropicBedrock
from src.utils.logging_utils import setup_logger
from src.config.config import settings

logger = setup_logger(__name__)

USE_BEDROCK = settings.ANTHROPIC_BEDROCK == 'true'

class AnthropicClientProtocol(Protocol):
    """Protocol defining the required interface for Anthropic clients."""
    
    async def messages(self) -> Any:
        ...

class BaseAnthropicClient(ABC):
    """Abstract base class for Anthropic clients."""
    
    _instance: Optional[Union[AsyncAnthropic, AsyncAnthropicBedrock]] = None
    
    @abstractmethod
    def get_client(self) -> Union[AsyncAnthropic, AsyncAnthropicBedrock]:
        """Get client instance."""
        pass

class DirectAnthropicClient(BaseAnthropicClient):
    """Direct Anthropic API client implementation."""
    
    @classmethod
    def get_client(cls) -> AsyncAnthropic:
        if cls._instance is None:
            api_key = settings.ANTHROPIC_API_KEY
            if not api_key:
                logger.error("ANTHROPIC_API_KEY environment variable not set")
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
                
            logger.debug("Creating new Direct Anthropic client instance")
            cls._instance = AsyncAnthropic(api_key=api_key)
            
        return cls._instance

class BedrockAnthropicClient(BaseAnthropicClient):
    """AWS Bedrock Anthropic client implementation."""
    
    @classmethod
    def get_client(cls) -> AsyncAnthropicBedrock:
        if cls._instance is None:
            if not all([settings.AWS_ACCESS_KEY, settings.AWS_SECRET_KEY, settings.AWS_REGION]):
                logger.error("AWS credentials not properly configured")
                raise ValueError("AWS credentials (AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION) must be set for Bedrock")
                
            logger.debug("Creating new Bedrock Anthropic client instance")
            cls._instance = AsyncAnthropicBedrock(
                aws_access_key=settings.AWS_ACCESS_KEY,
                aws_secret_key=settings.AWS_SECRET_KEY,
                aws_region=settings.AWS_REGION
            )
            
        return cls._instance

class AnthropicClientFactory:
    """Factory for creating appropriate Anthropic client."""
    
    @staticmethod
    def create_client() -> BaseAnthropicClient:
        """Create appropriate client based on configuration.
        
        Returns:
            BaseAnthropicClient: The appropriate client implementation
        """
        return BedrockAnthropicClient() if USE_BEDROCK else DirectAnthropicClient()

class AnthropicClient:
    """Main interface for Anthropic client operations."""
    
    _instance: Optional[BaseAnthropicClient] = None
    
    @classmethod
    def get_client(cls) -> Union[AsyncAnthropic, AsyncAnthropicBedrock]:
        """Get or create appropriate Anthropic client instance.
        
        Returns:
            Union[AsyncAnthropic, AsyncAnthropicBedrock]: The Anthropic client instance
            
        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set
        """
        if cls._instance is None:
            cls._instance = AnthropicClientFactory.create_client()
        return cls._instance.get_client()
    
    @classmethod
    async def create_message(
        cls,
        prompt: str,
        system_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Create a message using the Anthropic client with configured settings.
        
        Args:
            prompt: The user prompt to send
            system_prompt: The system prompt to use
            max_tokens: Optional max tokens override
            temperature: Optional temperature override
            
        Returns:
            str: The model's response text
            
        Raises:
            ValueError: If client creation fails
            Exception: If API call fails
        """
        client = cls.get_client()
        model = settings.AWS_BEDROCK_MODEL if USE_BEDROCK else settings.ANTHROPIC_MODEL
        
        try:
            message = await client.messages.create(
                model=model,
                max_tokens=max_tokens or settings.ANTHROPIC_MAX_TOKENS,
                system=system_prompt,
                temperature=temperature or settings.ANTHROPIC_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
            
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            raise 