"""Test configuration and fixtures."""
from src.repositories.classification_repo import ClassificationRepository
from src.main import app
from src.database.database_utils import get_database
from src.config.config import settings
from src.api.dependencies import get_classifications_collection, get_repository
from mongomock_motor import AsyncMongoMockClient
from fastapi.testclient import TestClient
from fastapi import FastAPI
import pytest
from unittest.mock import patch
from typing import AsyncGenerator, Generator
import asyncio
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Get the project root directory (one level up from tests)
project_root = str(Path(__file__).parent.parent)

# Add project root to Python path before any local imports
sys.path.append(project_root)

# Load test environment variables before any imports
load_dotenv(".env.test", override=True)

# Standard library imports

# Third-party imports

# Local imports


@pytest.fixture(scope="function")
async def mock_mongodb() -> AsyncGenerator[AsyncMongoMockClient, None]:
    """Create a mock MongoDB client for testing."""
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client[f"{settings.MONGO_INITDB_DATABASE}_test"]

    # Override all database access points
    app.dependency_overrides[get_database] = lambda: mock_db
    app.dependency_overrides[get_classifications_collection] = lambda: mock_db.classifications
    app.dependency_overrides[get_repository] = lambda: ClassificationRepository(
        mock_db.classifications)

    # Also patch the global database connection
    with patch('src.database.db', mock_db):
        yield mock_db

    # Clean up
    await mock_client.drop_database(settings.MONGO_INITDB_DATABASE)
    app.dependency_overrides.clear()
    mock_client.close()


@pytest.fixture(scope="function")
async def test_app(mock_mongodb) -> AsyncGenerator[FastAPI, None]:
    """Create a test instance of the FastAPI application with mocked MongoDB."""
    yield app


@pytest.fixture(scope="function")
def test_client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create a test client for making HTTP requests."""
    with TestClient(test_app) as client:
        yield client
