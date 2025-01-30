"""Database package initialization."""
from motor.motor_asyncio import AsyncIOMotorDatabase

db: AsyncIOMotorDatabase = None  # Global database instance
