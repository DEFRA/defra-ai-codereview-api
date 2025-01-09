"""Integration tests for health check endpoint."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

def test_health_check(
    test_app: FastAPI,
    test_client: TestClient
) -> None:
    """Test health check endpoint returns healthy status."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"} 