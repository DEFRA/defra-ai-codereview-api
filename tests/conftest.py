"""Test configuration and fixtures."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory (one level up from tests)
project_root = str(Path(__file__).parent.parent)

# Add project root to Python path
sys.path.append(project_root)

# Load test environment variables before any imports
load_dotenv(".env.test", override=True)

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from mongomock_motor import AsyncMongoMockClient

from src.main import app
from src.config import settings
from src.database import get_database

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_mongodb() -> AsyncGenerator[AsyncMongoMockClient, None]:
    """Create a mock MongoDB client."""
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client[f"{settings.MONGO_INITDB_DATABASE}_test"]
    yield mock_db
    await mock_client.drop_database(f"{settings.MONGO_INITDB_DATABASE}_test")
    mock_client.close()

@pytest.fixture
async def test_app(mock_mongodb) -> AsyncGenerator[FastAPI, None]:
    """Create a test instance of the FastAPI application with mocked MongoDB."""
    async def mock_get_database():
        return mock_mongodb
    
    app.dependency_overrides[get_database] = mock_get_database
    yield app
    app.dependency_overrides.clear()

@pytest.fixture
async def test_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for making HTTP requests."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client 