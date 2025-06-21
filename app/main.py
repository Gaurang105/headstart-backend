from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.models import WhatsAppMessage, ProcessedResponse
from app.services import content_processor

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    1. Extracts waId, senderName, and text from the WhatsApp message
    2. Detects if the URL is from YouTube or Instagram
    3. Fetches appropriate content data from the respective API
    4. Returns processed response with content data
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