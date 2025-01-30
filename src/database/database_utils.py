"""Database utilities."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from src.config.config import settings
from . import db
from .database_init import init_database


async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    global db
    if db is None:
        db = await init_database()
    return db
