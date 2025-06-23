from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import json

from app.config import settings
from app.models import WhatsAppMessage, ProcessedResponse, LoginRequest, LoginResponse, GetCitiesRequest, GetCitiesResponse, GetPoisRequest, PoiData, GetPoisResponse, GetLinksRequest, LinkData, GetLinksResponse
from app.services import content_processor
from app.database import connect_to_mongo, close_mongo_connection
from app.db_services import db_service

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

# Add custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors with request body for debugging"""
    try:
        # Try to get the request body
        body = await request.body()
        body_str = body.decode('utf-8') if body else "No body"
        
        print(f"Validation Error on {request.url.path}")
        print(f"Request body: {body_str}")
        print(f"Validation errors: {exc.errors()}")
        print(f"Request headers: {dict(request.headers)}")
        
    except Exception as e:
        print(f"Error logging validation error: {e}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": "Validation failed. Check server logs for details."
        }
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging"""
    if request.url.path == "/api/v1/process-message" and request.method == "POST":
        # Clone the body for logging (be careful with large bodies in production)
        body = await request.body()
        print(f"Incoming request to {request.url.path}")
        print(f"Headers: {dict(request.headers)}")
        print(f"Body: {body.decode('utf-8') if body else 'No body'}")
        
        # Recreate the request with the body we read
        from starlette.requests import Request as StarletteRequest
        request = StarletteRequest(request.scope, receive=lambda: {"type": "http.request", "body": body})
    
    response = await call_next(request)
    return response

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
    1. Returns HTTP 200 immediately to prevent WhatsApp retries
    2. Processes message asynchronously in background
    3. Uses message deduplication to prevent duplicate processing
    """
    try:
        # Check for message deduplication first
        message_id = message.whatsappMessageId or message.id or f"{message.waId}_{message.text}_{message.timestamp}"
        
        if message_id and await db_service.is_message_processed(message_id):
            # Message already processed, return success immediately
            return ProcessedResponse(
                success=True,
                link=message.text,
                locations=[],
                name=message.senderName,
                phoneNo=message.waId,
                error="Message already processed"
            )
        
        # Mark message as being processed to prevent duplicates
        if message_id:
            await db_service.mark_message_as_processed(message_id, message.waId, message.text)
        
        # Start background processing
        import asyncio
        asyncio.create_task(process_message_async(message))
        
        # Return immediate success response to prevent WhatsApp retries
        return ProcessedResponse(
            success=True,
            link=message.text,
            locations=[],
            name=message.senderName,
            phoneNo=message.waId,
            error="Processing started - check back later for results"
        )
        
    except Exception as e:
        print(f"Error starting message processing: {e}")
        return ProcessedResponse(
            success=False,
            link=message.text,
            name=message.senderName,
            phoneNo=message.waId,
            error=f"Error starting processing: {str(e)}"
        )

async def process_message_async(message: WhatsAppMessage):
    """Process message asynchronously in the background"""
    try:
        print(f"Starting async processing for message: {message.text}")
        result = await content_processor.process_message(message)
        print(f"Async processing completed for: {message.text}")
        print(f"Result: {result.model_dump()}")
    except Exception as e:
        print(f"Error in async processing: {e}")

@app.post("/api/v1/login", response_model=LoginResponse)
async def login_user(login_data: LoginRequest):
    """
    Simple login endpoint that registers user if they don't exist.
    
    This endpoint:
    1. Checks if user exists in the database by phoneNo
    2. If user exists: returns success with user_exists=True
    3. If user doesn't exist: creates new user with empty links and locations
    4. Returns login response with user details
    """
    try:
        # Check if user already exists
        existing_user = await db_service.get_user_data(login_data.phoneNo)
        
        if existing_user:
            # User exists, return success
            return LoginResponse(
                success=True,
                message="Login successful",
                user_exists=True,
                name=existing_user["name"],
                phoneNo=existing_user["phoneNo"]
            )
        else:
            # User doesn't exist, create new user
            created = await db_service.create_user(login_data.name, login_data.phoneNo)
            
            if created:
                return LoginResponse(
                    success=True,
                    message="User registered and logged in successfully",
                    user_exists=False,
                    name=login_data.name,
                    phoneNo=login_data.phoneNo
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/v1/getCities", response_model=GetCitiesResponse)
async def get_cities(request: GetCitiesRequest):
    """
    Get all unique cities for a user based on their phone number.
    
    This endpoint:
    1. Fetches user data by phoneNo
    2. Extracts unique cities from user's locations
    3. Returns list of cities with count
    """
    try:
        # Get user data by phone number
        user_data = await db_service.get_user_data(request.phoneNo)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Extract unique cities from user's locations
        cities = set()
        locations = user_data.get("locations", [])
        
        for location in locations:
            city = location.get("city", "").strip()
            if city:  # Only add non-empty cities
                cities.add(city)
        
        # Convert to sorted list
        cities_list = sorted(list(cities))
        
        return GetCitiesResponse(
            success=True,
            phoneNo=request.phoneNo,
            cities=cities_list,
            total_cities=len(cities_list),
            message=f"Found {len(cities_list)} unique cities for user"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/v1/getPois", response_model=GetPoisResponse)
async def get_pois(request: GetPoisRequest):
    """
    Get all POIs (Points of Interest) for a user based on their phone number.
    
    This endpoint:
    1. Fetches user data by phoneNo
    2. Returns all locations (POIs) for the user
    3. Each POI includes detailed information like name, category, coordinates, etc.
    """
    try:
        # Get user data by phone number
        user_data = await db_service.get_user_data(request.phoneNo)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Extract all locations (POIs) from user data
        locations = user_data.get("locations", [])
        pois = []
        
        for location in locations:
            poi = PoiData(
                poi_name=location.get("poi_name", ""),
                category=location.get("category", ""),
                geo_location=location.get("geo_location", [0.0, 0.0]),
                maps_url=location.get("maps_url", ""),
                website_url=location.get("website_url", ""),
                photos_links=location.get("photos_links", []),
                city=location.get("city", ""),
                tgid=location.get("tgid"),
                source_link=location.get("source_link", ""),
                added_at=location.get("added_at", "").isoformat() if hasattr(location.get("added_at", ""), 'isoformat') else str(location.get("added_at", ""))
            )
            pois.append(poi)
        
        return GetPoisResponse(
            success=True,
            phoneNo=request.phoneNo,
            pois=pois,
            total_pois=len(pois),
            message=f"Found {len(pois)} POIs for user"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/v1/getLinks", response_model=GetLinksResponse)
async def get_links(request: GetLinksRequest):
    """
    Get all links for a user based on their phone number.
    
    This endpoint:
    1. Fetches user data by phoneNo
    2. Returns all links for the user
    3. Each link includes URL and timestamp when it was added
    """
    try:
        # Get user data by phone number
        user_data = await db_service.get_user_data(request.phoneNo)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Extract all links from user data
        user_links = user_data.get("links", [])
        links = []
        
        for link in user_links:
            link_data = LinkData(
                url=link.get("url", ""),
                added_at=link.get("added_at", "").isoformat() if hasattr(link.get("added_at", ""), 'isoformat') else str(link.get("added_at", ""))
            )
            links.append(link_data)
        
        # Sort links by added_at in descending order (newest first)
        links.sort(key=lambda x: x.added_at, reverse=True)
        
        return GetLinksResponse(
            success=True,
            phoneNo=request.phoneNo,
            links=links,
            total_links=len(links),
            message=f"Found {len(links)} links for user"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/v1/processing-status/{phone_no}")
async def get_processing_status(phone_no: str):
    """
    Get the current processing status and recent results for a user.
    This can be used to check if background processing is complete.
    """
    try:
        # Get user's recent links to see latest processed data
        user_data = await db_service.get_user_data(phone_no)
        
        if not user_data:
            return {
                "success": False,
                "message": "User not found",
                "phone_no": phone_no
            }
        
        # Get latest link and locations
        links = user_data.get("links", [])
        locations = user_data.get("locations", [])
        
        # Sort by added_at to get most recent
        if links:
            latest_link = max(links, key=lambda x: x.get("added_at", datetime.min))
            recent_locations = [
                loc for loc in locations 
                if loc.get("source_link") == latest_link.get("url")
            ]
        else:
            latest_link = None
            recent_locations = []
        
        return {
            "success": True,
            "phone_no": phone_no,
            "latest_link": latest_link,
            "recent_locations": recent_locations,
            "total_links": len(links),
            "total_locations": len(locations),
            "message": "Processing status retrieved successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving status: {str(e)}",
            "phone_no": phone_no
        }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
