"""Integration tests for the health check endpoint.

This module verifies that the application's health check endpoint
is functioning correctly and returning appropriate status.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_health_check_returns_healthy_status(
    test_app: FastAPI,
    test_client: TestClient
) -> None:
    """
    Test health check endpoint functionality.
    
    Given: A running FastAPI application
    When: Making a GET request to /health endpoint
    Then: Should return 200 with healthy status
    """
    # When
    response = test_client.get("/health")
    
    # Then
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"} 