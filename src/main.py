"""Main FastAPI application."""
from fastapi import FastAPI
from src.api.v1 import code_reviews, classifications, standard_sets

app = FastAPI(title="Code Review API")

# Add API routes
app.include_router(code_reviews.router, prefix="/api/v1", tags=["code-reviews"])
app.include_router(classifications.router, prefix="/api/v1", tags=["classifications"])
app.include_router(
    standard_sets.router,
    prefix="/api/v1",
    tags=["standard-sets"]
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 