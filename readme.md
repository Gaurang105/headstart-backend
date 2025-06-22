# Headstart Backend

A FastAPI-based backend service for the Headstart application that processes WhatsApp bot messages, manages user data, and provides APIs for fetching user-specific content including locations, POIs, and links from YouTube and Instagram.

## Features

- **User Management**: Simple login/registration with phone number authentication
- **WhatsApp Message Processing**: Extracts and processes content from WhatsApp bot messages
- **Multi-Platform Support**: Handles YouTube and Instagram content URLs
- **Location & POI Management**: Stores and retrieves Points of Interest from user's saved content
- **Link Management**: Tracks all links processed by users
- **City Analytics**: Provides unique cities from user's saved locations
- **MongoDB Integration**: Persistent storage with user collections and global link caching

## API Endpoints

### User Management

#### POST `/api/v1/login`
Simple login endpoint that registers user if they don't exist.

**Request Body**:
```json
{
  "name": "John Doe",
  "phoneNo": "+1234567890"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Login successful",
  "user_exists": true,
  "name": "John Doe",
  "phoneNo": "+1234567890"
}
```

### User Data Retrieval

#### POST `/api/v1/getCities`
Get all unique cities for a user based on their phone number.

**Request Body**:
```json
{
  "phoneNo": "+1234567890"
}
```

**Response**:
```json
{
  "success": true,
  "phoneNo": "+1234567890",
  "cities": ["Delhi", "Mumbai", "Paris", "Tokyo"],
  "total_cities": 4,
  "message": "Found 4 unique cities for user"
}
```

#### POST `/api/v1/getPois`
Get all POIs (Points of Interest) for a user based on their phone number.

**Request Body**:
```json
{
  "phoneNo": "+1234567890"
}
```

**Response**:
```json
{
  "success": true,
  "phoneNo": "+1234567890",
  "pois": [
    {
      "poi_name": "Eiffel Tower",
      "category": "Tourist Attraction",
      "geo_location": [48.8584, 2.2945],
      "maps_url": "https://maps.google.com/...",
      "website_url": "https://www.toureiffel.paris/",
      "photos_links": [],
      "city": "Paris",
      "tgid": "ChIJLU7jZClu5kcR4PcOOO6p3I0",
      "source_link": "https://youtube.com/watch?v=abc123",
      "added_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total_pois": 1,
  "message": "Found 1 POIs for user"
}
```

#### POST `/api/v1/getLinks`
Get all links for a user based on their phone number.

**Request Body**:
```json
{
  "phoneNo": "+1234567890"
}
```

**Response**:
```json
{
  "success": true,
  "phoneNo": "+1234567890",
  "links": [
    {
      "url": "https://youtube.com/watch?v=abc123",
      "added_at": "2024-01-16T14:20:00Z"
    }
  ],
  "total_links": 1,
  "message": "Found 1 links for user"
}
```

### Content Processing

#### POST `/api/v1/process-message`
Process a complete WhatsApp message and fetch content data.

**Request Body**: WhatsApp message object with `text`, `waId`, `senderName`
**Response**: Processed response with content data and locations

### Health Check

#### GET `/health`
Health check endpoint for monitoring.

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Environment**
   ```bash
   cp .env.example .env
   # Configure MongoDB connection and other settings in .env
   ```

3. **Run the Application**
   ```bash
   # Development mode
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Or use Python directly
   python -m app.main
   ```

4. **Access the API**
   - API: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - OpenAPI Schema: http://localhost:8000/openapi.json

## Database Schema

### Users Collection
```json
{
  "name": "John Doe",
  "phoneNo": "+1234567890",
  "links": [
    {
      "url": "https://youtube.com/watch?v=abc123",
      "added_at": "2024-01-15T10:30:00Z"
    }
  ],
  "locations": [
    {
      "poi_name": "Eiffel Tower",
      "category": "Tourist Attraction",
      "geo_location": [48.8584, 2.2945],
      "maps_url": "https://maps.google.com/...",
      "website_url": "https://www.toureiffel.paris/",
      "photos_links": [],
      "city": "Paris",
      "tgid": "ChIJLU7jZClu5kcR4PcOOO6p3I0",
      "source_link": "https://youtube.com/watch?v=abc123",
      "added_at": "2024-01-15T10:30:00Z"
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Global Links Collection
```json
{
  "link": "https://youtube.com/watch?v=abc123",
  "author": "Channel Name",
  "locations": [...],
  "processed_at": "2024-01-15T10:30:00Z",
  "processed_count": 5
}
```

## Supported Platforms

### YouTube
- Fetches video/short information including title, description, views, likes
- Retrieves complete transcript with timestamps
- Gets channel information and related videos
- Extracts location data from video content

### Instagram
- Fetches media transcript for posts and reels
- Handles carousel posts with multiple transcripts
- AI-powered transcript generation
- Extracts location information from posts

## Data Flow

### User Registration/Login Flow
1. User sends name and phoneNo to `/api/v1/login`
2. System checks if user exists by phoneNo
3. If user doesn't exist, creates new user with empty links and locations
4. Returns success response with user details

### Content Processing Flow
1. WhatsApp bot sends message data to `/api/v1/process-message`
2. API extracts `waId`, `senderName`, and `text` (URL) from the message
3. System checks if link exists in global cache
4. If not cached, makes API call to ScrapeCreators service to extract content and locations
5. Saves content to global cache and updates user's links and locations
6. Returns processed response with location data

### User Data Retrieval Flow
1. Client sends phoneNo to respective endpoints (`/getCities`, `/getPois`, `/getLinks`)
2. System fetches user data using phoneNo as primary key
3. Processes and returns requested data (cities, POIs, or links)

## Error Handling

The API includes comprehensive error handling:
- Input validation using Pydantic models
- HTTP error handling for external API calls
- 404 responses for non-existent users
- Graceful degradation for unsupported platforms
- Detailed error messages in responses
- Database connection error handling

## Tech Stack

- **FastAPI**: Modern, fast web framework
- **MongoDB**: NoSQL database for user and content storage
- **Motor**: Async MongoDB driver
- **Pydantic**: Data validation and serialization
- **httpx**: Async HTTP client for external API calls
- **uvicorn**: ASGI server for running the application

## Development

### Project Structure
```
headstart-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application and endpoints
│   ├── models.py            # Pydantic models for API requests/responses
│   ├── db_models.py         # Database document models
│   ├── services.py          # Business logic for content processing
│   ├── db_services.py       # Database operations
│   ├── database.py          # MongoDB connection and configuration
│   ├── config.py            # Configuration settings
│   └── analysis/            # Content analysis modules
│       ├── extract_locations.py
│       └── process_google_places.py
├── requirements.txt         # Dependencies
├── .env.example            # Environment template
├── README.md               # Documentation
└── run.py 
```

## Environment Configuration

Required environment variables:
```bash
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=headstart
API_TITLE=Headstart Backend API
API_VERSION=1.0.0
DEBUG=true
```

## Production Deployment

For production deployment, consider:
- Setting `DEBUG=false` in environment
- Configuring proper CORS origins
- Using a production ASGI server like Gunicorn
- Setting up proper logging and monitoring
- Implementing rate limiting and authentication

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test your implementation
5. Submit a pull request