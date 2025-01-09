"""Integration tests for health check endpoint."""
import pytest
from httpx import AsyncClient
from fastapi import FastAPI, status

pytestmark = pytest.mark.asyncio

async def test_health_check(
    test_app: FastAPI,
    test_client: AsyncClient
) -> None:
    """Test health check endpoint returns healthy status."""
    response = await test_client.get("/health")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"} 