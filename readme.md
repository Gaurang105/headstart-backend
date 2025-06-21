# Headstart Backend

A FastAPI-based backend service for the Headstart application that processes WhatsApp bot messages and fetches content data from YouTube and Instagram.

## Features

- **WhatsApp Message Processing**: Extracts key data from WhatsApp bot messages
- **Multi-Platform Support**: Handles YouTube and Instagram content URLs
- **Content Data Fetching**: Retrieves video/media information and transcripts

## API Endpoints

### POST `/api/v1/process-message`
Process a complete WhatsApp message and fetch content data.

**Request Body**: WhatsApp message object
**Response**: Processed response with content data

### GET `/health`
Health check endpoint for monitoring.

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   # Development mode
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Or use Python directly
   python -m app.main
   ```

3. **Access the API**
   - API: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - OpenAPI Schema: http://localhost:8000/openapi.json

## Supported Platforms

### YouTube
- Fetches video/short information including title, description, views, likes
- Retrieves complete transcript with timestamps
- Gets channel information and related videos

### Instagram
- Fetches media transcript for posts and reels
- Handles carousel posts with multiple transcripts
- AI-powered transcript generation

## Environment Configuration

Copy `.env.example` to `.env` and customize as needed:

```bash
cp .env.example .env
```

## Data Flow

1. WhatsApp bot sends message data to `/api/v1/process-message`
2. API extracts `waId`, `senderName`, and `text` (URL) from the message
3. System detects if URL is from YouTube or Instagram
4. Makes appropriate API call to ScrapeCreators service
5. Returns processed response with content data

## Error Handling

The API includes comprehensive error handling:
- Input validation using Pydantic models
- HTTP error handling for external API calls
- Graceful degradation for unsupported platforms
- Detailed error messages in responses

## Tech Stack

- **FastAPI**: Modern, fast web framework
- **Pydantic**: Data validation and serialization
- **httpx**: Async HTTP client for external API calls
- **uvicorn**: ASGI server for running the application

## Development

### Project Structure
```
headstart-backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── models.py        # Pydantic models
│   ├── services.py      # Business logic
│   └── config.py        # Configuration
├── requirements.txt     # Dependencies
├── .env.example        # Environment template
├── README.md           # Documentation
└── run.py 
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
5. Submit a pull request