import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # API Configuration
    API_TITLE = "Headstart Backend API"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "Backend API for Headstart application handling WhatsApp bot data"
    
    # External API Configuration
    SCRAPE_CREATORS_API_KEY = os.getenv("SCRAPE_CREATORS_API_KEY")
    YOUTUBE_API_URL = "https://api.scrapecreators.com/v1/youtube/video"
    INSTAGRAM_API_URL = "https://api.scrapecreators.com/v2/instagram/media/transcript"
    
    # Location extraction API keys
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
    
    # MongoDB Configuration
    MONGODB_URL = os.getenv("MONGODB_URL")
    DATABASE_NAME = os.getenv("DATABASE_NAME")
    
    # Request timeout in seconds
    REQUEST_TIMEOUT = 60
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT")
    DEBUG = os.getenv("DEBUG")


settings = Settings()
