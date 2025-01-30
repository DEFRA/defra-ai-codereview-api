"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1 import code_reviews, classifications, standard_sets
from src.database.database_utils import get_database

app = FastAPI(
    title="Code Review API"
)

# Add API routes
app.include_router(
    code_reviews.router,
    prefix="/api/v1",
    tags=["code-reviews"]
)

app.include_router(
    classifications.router,
    prefix="/api/v1",
    tags=["classifications"]
)

app.include_router(
    standard_sets.router,
    prefix="/api/v1",
    tags=["standard-sets"]
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await get_database()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 