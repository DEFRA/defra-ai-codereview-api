"""MongoDB database connection and initialization."""
from motor.motor_asyncio import AsyncIOMotorClient
from src.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client.code_reviews

async def get_database():
    """Get database connection."""
    return db 