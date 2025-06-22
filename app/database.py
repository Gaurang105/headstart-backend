from motor.motor_asyncio import AsyncIOMotorClient
import logging
import ssl

from app.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None

# Create database instance
db = Database()

async def connect_to_mongo():
    """Create database connection"""
    try:
        # Configure SSL context for MongoDB Atlas
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create MongoDB client with SSL configuration
        db.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            ssl_context=ssl_context,
            tlsInsecure=True,
            serverSelectionTimeoutMS=30000,
            socketTimeoutMS=20000,
            connectTimeoutMS=20000,
            retryWrites=True,
            w="majority"
        )
        
        db.database = db.client[settings.DATABASE_NAME]
        
        # Test the connection
        await db.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")

async def create_indexes():
    """Create database indexes for optimal performance"""
    try:
        # Global collection indexes
        global_collection = db.database.global_links
        await global_collection.create_index("link", unique=True)
        await global_collection.create_index([("locations.geo_location", "2dsphere")])
        
        # User collection indexes
        user_collection = db.database.users
        await user_collection.create_index("phoneNo", unique=True)
        await user_collection.create_index([("locations.geo_location", "2dsphere")])
        await user_collection.create_index("links.url")
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")

def get_database():
    """Get database instance"""
    return db.database

# Collection accessors
def get_global_collection():
    """Get global links collection"""
    return db.database.global_links

def get_users_collection():
    """Get users collection"""
    return db.database.users
