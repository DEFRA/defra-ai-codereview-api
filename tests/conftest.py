"""Test configuration and fixtures."""
from src.repositories.classification_repo import ClassificationRepository
from src.repositories.code_review_repo import CodeReviewRepository
from src.repositories.standard_set_repo import StandardSetRepository
from src.main import app
from src.database.database_utils import get_database
from src.config.config import settings
from src.api.dependencies import (
    get_classifications_collection,
    get_repository,
    get_code_reviews_collection,
    get_standard_sets_collection,
    get_standard_set_repo,
    get_code_review_repo
)
from mongomock_motor import AsyncMongoMockClient
from fastapi.testclient import TestClient
from fastapi import FastAPI
import pytest
from unittest.mock import patch, AsyncMock
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

    # Initialize collections with schema validation
    await mock_db.create_collection("classifications")
    await mock_db.create_collection("standard_sets")
    await mock_db.create_collection("standards")
    await mock_db.create_collection("code_reviews")

    # Create repository instances with collections
    code_review_repo = CodeReviewRepository(mock_db.code_reviews)
    standard_set_repo = StandardSetRepository(mock_db.standard_sets)
    classification_repo = ClassificationRepository(mock_db.classifications)

    # Override all database and repository dependencies
    app.dependency_overrides.update({
        get_database: lambda: mock_db,
        get_classifications_collection: lambda: mock_db.classifications,
        get_code_reviews_collection: lambda: mock_db.code_reviews,
        get_standard_sets_collection: lambda: mock_db.standard_sets,
        get_repository: lambda: classification_repo,
        get_code_review_repo: lambda: code_review_repo,
        get_standard_set_repo: lambda: standard_set_repo,
    })

    # Patch all database operations
    with patch('src.database.database_init.init_database', AsyncMock(return_value=mock_db)), \
            patch('src.database.database_utils.init_database', AsyncMock(return_value=mock_db)), \
            patch('motor.motor_asyncio.AsyncIOMotorClient', return_value=mock_client):
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
