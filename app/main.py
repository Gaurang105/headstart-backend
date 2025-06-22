from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.models import WhatsAppMessage, ProcessedResponse, LoginRequest, LoginResponse, GetCitiesRequest, GetCitiesResponse, GetPoisRequest, PoiData, GetPoisResponse
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

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
