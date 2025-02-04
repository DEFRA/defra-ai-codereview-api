"""Test fixtures for the FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from src.main import app

@pytest.fixture(autouse=True)
async def mock_database_setup():
    """Mock all database-related components."""
    mock_db = AsyncMock()
    mock_db.client = MagicMock()

    # Add attributes for each collection used across repositories
    for col in ["classifications", "code_reviews", "standard_sets", "standards"]:
        collection_mock = AsyncMock()
        collection_mock.database = mock_db
        setattr(mock_db, col, collection_mock)

    with patch("src.main.init_database", return_value=mock_db), \
         patch("src.database.database_utils.client", new=MagicMock()), \
         patch("src.database.database_utils.get_database", return_value=mock_db), \
         patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=MagicMock()):
        
        app.state.db = mock_db
        yield mock_db

@pytest.fixture(autouse=True)
async def reset_app_state():
    """Reset application state before each test."""
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client(mock_database_setup):
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
async def async_client(mock_database_setup):
    """Create an async test client for the FastAPI application.
    
    Uses ASGITransport to make requests directly to the FastAPI app
    without making real HTTP calls.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables."""
    monkeypatch.setenv("MONGODB_URL", "mongodb://test:27017")
    monkeypatch.setenv("DATABASE_NAME", "test_db")