import httpx
import re
from typing import Optional, List

from app.config import settings
from app.models import (
    WhatsAppMessage, 
    ExtractedData, 
    YouTubeResponse, 
    InstagramResponse,
    ProcessedResponse,
    LocationData
)
from app.analysis.extract_locations import ExtractLocations, VideoType
from app.db_services import db_service

class ContentProcessor:
    """Service class for processing WhatsApp messages and fetching content data."""
    
    def __init__(self):
        self.youtube_api_url = settings.YOUTUBE_API_URL
        self.instagram_api_url = settings.INSTAGRAM_API_URL
        self.api_key = settings.SCRAPE_CREATORS_API_KEY
        self.timeout = settings.REQUEST_TIMEOUT
        
        # Initialize location extractor
        try:
            self.location_extractor = ExtractLocations()
        except Exception as e:
            print(f"Warning: Location extractor not available - {e}")
            self.location_extractor = None
    
    def extract_data_from_message(self, message: WhatsAppMessage) -> ExtractedData:
        """Extract required data from WhatsApp message."""
        platform = self.detect_platform(message.text)
        
        return ExtractedData(
            waId=message.waId,
            senderName=message.senderName,
            text=message.text,
            platform=platform
        )
    
    def detect_platform(self, url: str) -> str:
        """Detect if the URL is from YouTube or Instagram."""
        url_lower = url.lower()
        
        # YouTube patterns
        youtube_patterns = [
            r'youtube\.com',
            r'youtu\.be',
            r'm\.youtube\.com'
        ]
        
        # Instagram patterns
        instagram_patterns = [
            r'instagram\.com',
            r'instagr\.am'
        ]
        
        for pattern in youtube_patterns:
            if re.search(pattern, url_lower):
                return 'youtube'
        
        for pattern in instagram_patterns:
            if re.search(pattern, url_lower):
                return 'instagram'
        
        return 'unknown'
    
    async def fetch_youtube_data(self, url: str) -> Optional[YouTubeResponse]:
        """Fetch YouTube video data from ScrapeCreators API."""
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        params = {
            'url': url,
            'get_transcript': True
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.youtube_api_url,
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                print("YouTube API Response:", data)
                return YouTubeResponse(**data)
                
        except httpx.HTTPError as e:
            print(f"HTTP error occurred while fetching YouTube data: {e}")
            return None
        except Exception as e:
            print(f"Error occurred while fetching YouTube data: {e}")
            return None
    
    async def fetch_instagram_data(self, url: str) -> Optional[InstagramResponse]:
        """Fetch Instagram media transcript from ScrapeCreators API."""
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        params = {
            'url': url
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.instagram_api_url,
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                print("Instagram API Response:", data)
                return InstagramResponse(**data)
                
        except httpx.HTTPError as e:
            print(f"HTTP error occurred while fetching Instagram data: {e}")
            return None
        except Exception as e:
            print(f"Error occurred while fetching Instagram data: {e}")
            return None
    
    def extract_locations_from_content(self, content_data: dict, platform: str) -> Optional[List[dict]]:
        """Extract locations from content data."""
        if not self.location_extractor:
            print("Location extractor not available")
            return None
            
        try:
            video_type = VideoType.YOUTUBE if platform == 'youtube' else VideoType.INSTAGRAM
            locations_raw = self.location_extractor.extract_locations(content_data, video_type)
            
            if locations_raw:
                # Filter out locations with [0.0, 0.0] coordinates
                valid_locations = []
                for loc in locations_raw:
                    geo_location = loc.get('geo_location', [0.0, 0.0])
                    if geo_location != [0.0, 0.0]:
                        valid_locations.append(loc)
                
                print(f"Extracted {len(valid_locations)} valid locations from {platform} content")
                return valid_locations
            else:
                print(f"No locations found in {platform} content")
                return []
                
        except Exception as e:
            print(f"Error extracting locations: {e}")
            return []
    
    async def fetch_content_and_locations(self, link: str, platform: str) -> tuple[Optional[dict], Optional[str], List[dict]]:
        """Fetch content data and extract locations."""
        content_data = None
        author = None
        locations = []
        
        try:
            if platform == 'youtube':
                youtube_data = await self.fetch_youtube_data(link)
                if youtube_data:
                    content_data = youtube_data.model_dump()
                    channel = content_data.get('channel', {})
                    author = channel.get('handle') if isinstance(channel, dict) else None
                    locations = self.extract_locations_from_content(content_data, 'youtube') or []
            
            elif platform == 'instagram':
                instagram_data = await self.fetch_instagram_data(link)
                if instagram_data:
                    content_data = instagram_data.model_dump()
                    # Instagram doesn't have author/handle in the same way
                    author = None
                    locations = self.extract_locations_from_content(content_data, 'instagram') or []
            
            return content_data, author, locations
        
        except Exception as e:
            print(f"Error fetching content and locations: {e}")
            return None, None, []
    
    async def process_message(self, message: WhatsAppMessage) -> ProcessedResponse:
        """Process WhatsApp message with database caching."""
        try:
            # Extract data from message
            extracted_data = self.extract_data_from_message(message)
            
            if extracted_data.platform == 'unknown':
                return ProcessedResponse(
                    success=False,
                    link=extracted_data.text,
                    name=extracted_data.senderName,
                    phoneNo=extracted_data.waId,
                    error="URL platform not supported. Only YouTube and Instagram are supported."
                )
            
            link = extracted_data.text
            phone_no = extracted_data.waId
            name = extracted_data.senderName
            
            # Step 1: Check if link exists in global database
            print(f"Checking global database for link: {link}")
            global_data = await db_service.get_global_link_data(link)
            
            if global_data:
                # Link exists in database - use cached data
                print("Link found in global database - using cached data")
                locations = global_data.get('locations', [])
                author = global_data.get('author')
                
                # Increment processed count
                await db_service.increment_processed_count(link)
                
                # Update user data
                await db_service.update_user_data(phone_no, name, link, locations)
                
            else:
                # Link doesn't exist - fetch fresh data
                print("Link not found in global database - fetching fresh data")
                content_data, author, locations = await self.fetch_content_and_locations(
                    link, extracted_data.platform
                )
                
                if content_data is None:
                    return ProcessedResponse(
                        success=False,
                        link=link,
                        name=name,
                        phoneNo=phone_no,
                        error=f"Failed to fetch {extracted_data.platform} data"
                    )
                
                # Save to global database
                await db_service.save_global_link_data(link, author, locations)
                
                # Update user data
                await db_service.update_user_data(phone_no, name, link, locations)
            
            # Convert locations to LocationData objects for response
            location_objects = []
            for loc in locations:
                location_data = LocationData(
                    poi_name=loc.get('poi_name', ''),
                    category=loc.get('category', ''),
                    geo_location=loc.get('geo_location', [0.0, 0.0]),
                    maps_url=loc.get('maps_url', ''),
                    website_url=loc.get('website_url', ''),
                    photos_links=loc.get('photos_links', []),
                    city=loc.get('city', ''),
                    tgid=loc.get('tgid')
                )
                location_objects.append(location_data)
            
            final_response = ProcessedResponse(
                success=True,
                link=link,
                locations=location_objects,
                author=author,
                name=name,
                phoneNo=phone_no
            )
            
            print("Final API Response:", final_response.model_dump())
            return final_response
            
        except Exception as e:
            print(f"Error processing message: {e}")
            return ProcessedResponse(
                success=False,
                link=message.text,
                name=message.senderName,
                phoneNo=message.waId,
                error=f"Error processing message: {str(e)}"
            )

# Create singleton instance
content_processor = ContentProcessor()
