"""Main FastAPI application."""
from fastapi import FastAPI
from src.api.v1 import code_reviews, classifications

app = FastAPI(title="Code Review API")

# Add API routes
app.include_router(code_reviews.router, prefix="/api/v1")
app.include_router(classifications.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 