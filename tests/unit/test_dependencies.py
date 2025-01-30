"""Unit tests for dependency injection functions.

This module tests the core functionality for:
1. Database connection management
2. Collection access
3. Repository instantiation
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from src.api.dependencies import (
    get_database,
    get_classifications_collection,
    get_standard_sets_collection,
)
from src.config.config import settings
from src.repositories.classification_repo import ClassificationRepository

@pytest.mark.asyncio
async def test_get_classifications_collection():
    """
    Test getting classifications collection.
    
    Given: MongoDB connection settings
    When: Getting classifications collection
    Then: Should yield collection and close client
    """
    mock_client = AsyncMock(spec=AsyncIOMotorClient)
    mock_db = AsyncMock()
    mock_collection = AsyncMock(spec=AsyncIOMotorCollection)
    
    # Configure the mock database to return our mock collection
    mock_db.classifications = mock_collection
    mock_client.__getitem__.return_value = mock_db
    
    with patch('src.dependencies.AsyncIOMotorClient', return_value=mock_client):
        async for collection in get_classifications_collection():
            assert collection == mock_collection
            mock_client.__getitem__.assert_called_once_with(settings.MONGO_INITDB_DATABASE)
        
        mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_get_repository():
    """
    Test getting repository instance.
    
    Given: A MongoDB collection
    When: Getting repository instance
    Then: Should return ClassificationRepository instance
    """
    mock_collection = AsyncMock(spec=AsyncIOMotorCollection)
    repository = await get_repository(mock_collection)
    
    assert isinstance(repository, ClassificationRepository)
    assert repository.collection == mock_collection

@pytest.mark.asyncio
async def test_get_database():
    """
    Test getting database connection.
    
    Given: MongoDB connection settings
    When: Getting database connection
    Then: Should yield database and close client
    """
    mock_client = AsyncMock(spec=AsyncIOMotorClient)
    mock_db = AsyncMock()
    
    mock_client.__getitem__.return_value = mock_db
    
    with patch('src.dependencies.AsyncIOMotorClient', return_value=mock_client):
        async for db in get_database():
            assert db == mock_db
            mock_client.__getitem__.assert_called_once_with(settings.MONGO_INITDB_DATABASE)
        
        mock_client.close.assert_called_once() 