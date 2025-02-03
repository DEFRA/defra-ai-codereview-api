"""Main FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import classifications, code_reviews, standard_sets
from src.config.config import settings
from src.database.database_init import init_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database connection."""
    try:
        # Startup: create database connection
        app.state.db = await init_database()
        yield
    finally:
        # Shutdown: close database connection
        if hasattr(app.state, 'db') and hasattr(app.state.db, 'client'):
            app.state.db.client.close()

app = FastAPI(
    title="Defra AI Code Review API",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(classifications.router, prefix="/api/v1", tags=["Classifications"])
app.include_router(code_reviews.router, prefix="/api/v1", tags=["Code Reviews"])
app.include_router(standard_sets.router, prefix="/api/v1", tags=["Standard Sets"])

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 