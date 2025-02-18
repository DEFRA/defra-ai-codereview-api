"""MongoDB database connection and initialization."""
from motor.motor_asyncio import AsyncIOMotorClient
from src.config.config import settings
from src.database.database_init import init_database

# Initialize database with schema validation
client = AsyncIOMotorClient(settings.MONGO_URI)
db = None

async def get_database():
    """Get database connection with schema validation."""
    global db
    if db is None:
        db = await init_database()
    return db