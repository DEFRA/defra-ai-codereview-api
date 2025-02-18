"""Singleton Anthropic client utility."""
import os
from typing import Optional, List, Dict, Any
from anthropic import AsyncAnthropic
from src.utils.logging_utils import setup_logger
from src.config.config import settings

logger = setup_logger(__name__)

class AnthropicClient:
    """Singleton class for Anthropic client."""
    
    _instance: Optional[AsyncAnthropic] = None
    
    @classmethod
    def get_client(cls) -> AsyncAnthropic:
        """Get or create Anthropic client instance.
        
        Returns:
            AsyncAnthropic: The Anthropic client instance
            
        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set
        """
        if cls._instance is None:
            api_key = settings.ANTHROPIC_API_KEY
            if not api_key:
                logger.error("ANTHROPIC_API_KEY environment variable not set")
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
                
            logger.debug("Creating new Anthropic client instance")
            cls._instance = AsyncAnthropic(api_key=api_key)
            
        return cls._instance
    
    @classmethod
    async def create_message(
        cls,
        prompt: str,
        system_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Create a message using the Anthropic client with configured settings.
        
        Args:
            prompt: The user prompt to send
            system_prompt: The system prompt to use
            model: Optional model override
            max_tokens: Optional max tokens override
            temperature: Optional temperature override
            
        Returns:
            str: The model's response text
            
        Raises:
            ValueError: If client creation fails
            Exception: If API call fails
        """
        client = cls.get_client()
        
        try:
            message = await client.messages.create(
                model=model or settings.ANTHROPIC_MODEL,
                max_tokens=max_tokens or settings.ANTHROPIC_MAX_TOKENS,
                system=system_prompt,
                temperature=temperature or settings.ANTHROPIC_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
            
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            raise 