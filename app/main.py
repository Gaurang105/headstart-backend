from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.models import WhatsAppMessage, ProcessedResponse
from app.services import content_processor
from app.database import connect_to_mongo, close_mongo_connection

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Connect to MongoDB on startup"""
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection on shutdown"""
    await close_mongo_connection()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "message": "Headstart Backend API is running",
        "version": settings.API_VERSION,
        "status": "healthy"
    }

@app.post("/api/v1/process-message", response_model=ProcessedResponse)
async def process_whatsapp_message(message: WhatsAppMessage):
    """
    Process WhatsApp message and extract content data.
    
    This endpoint:
    1. Checks if link exists in global database (cache)
    2. If exists: fetches data from cache and updates user
    3. If not exists: makes API calls, saves to global cache, updates user
    4. Returns processed response with locations
    """
    try:
        result = await content_processor.process_message(message)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
