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
        platform = self.detect_platform(message.text)
        
        return ExtractedData(
            waId=message.waId,
            senderName=message.senderName,
            text=message.text,
            platform=platform
        )
    
    def detect_platform(self, url: str) -> str:
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
                return YouTubeResponse(**data)
                
        except httpx.HTTPError as e:
            print(f"HTTP error occurred while fetching YouTube data: {e}")
            return None
        except Exception as e:
            print(f"Error occurred while fetching YouTube data: {e}")
            return None
    
    async def fetch_instagram_data(self, url: str) -> Optional[InstagramResponse]:
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
                return InstagramResponse(**data)
                
        except httpx.HTTPError as e:
            print(f"HTTP error occurred while fetching Instagram data: {e}")
            return None
        except Exception as e:
            print(f"Error occurred while fetching Instagram data: {e}")
            return None
    
    def extract_locations_from_content(self, content_data: dict, platform: str) -> Optional[List[LocationData]]:
        """Extract locations from content data."""
        if not self.location_extractor:
            print("Location extractor not available")
            return None
            
        try:
            video_type = VideoType.YOUTUBE if platform == 'youtube' else VideoType.INSTAGRAM
            locations_raw = self.location_extractor.extract_locations(content_data, video_type)
            
            if locations_raw:
                # Convert to LocationData objects
                locations = []
                for loc in locations_raw:
                    geo_location = loc.get('geo_location', [0.0, 0.0])
                    # Skip locations with [0.0, 0.0] coordinates
                    if geo_location != [0.0, 0.0]:
                        location_data = LocationData(
                            poi_name=loc.get('poi_name', ''),
                            category=loc.get('category', ''),
                            geo_location=geo_location,
                            maps_url=loc.get('maps_url', ''),
                            website_url=loc.get('website_url', ''),
                            photos_links=loc.get('photos_links', []),
                            city=loc.get('city', ''),
                            tgid=loc.get('tgid')
                        )
                        locations.append(location_data)
                
                print(f"Extracted {len(locations)} locations from {platform} content")
                return locations
            else:
                print(f"No locations found in {platform} content")
                return None
                
        except Exception as e:
            print(f"Error extracting locations: {e}")
            return None
    
    async def process_message(self, message: WhatsAppMessage) -> ProcessedResponse:
        try:
            extracted_data = self.extract_data_from_message(message)
            
            if extracted_data.platform == 'unknown':
                return ProcessedResponse(
                    success=False,
                    link=extracted_data.text,
                    name=extracted_data.senderName,
                    phoneNo=extracted_data.waId,
                    error="URL platform not supported. Only YouTube and Instagram are supported."
                )
            
            content_data = None
            locations = None
            
            if extracted_data.platform == 'youtube':
                youtube_data = await self.fetch_youtube_data(extracted_data.text)
                if youtube_data:
                    content_data = youtube_data.model_dump()
                    # Extract locations from YouTube data
                    locations = self.extract_locations_from_content(content_data, 'youtube')
                else:
                    return ProcessedResponse(
                        success=False,
                        link=extracted_data.text,
                        name=extracted_data.senderName,
                        phoneNo=extracted_data.waId,
                        error="Failed to fetch YouTube data"
                    )
            
            elif extracted_data.platform == 'instagram':
                instagram_data = await self.fetch_instagram_data(extracted_data.text)
                if instagram_data:
                    content_data = instagram_data.model_dump()
                    # Extract locations from Instagram data
                    locations = self.extract_locations_from_content(content_data, 'instagram')
                else:
                    return ProcessedResponse(
                        success=False,
                        link=extracted_data.text,
                        name=extracted_data.senderName,
                        phoneNo=extracted_data.waId,
                        error="Failed to fetch Instagram data"
                    )
            
            # Extract author from content data
            author = None
            
            if content_data:
                channel = content_data.get('channel', {})
                author = channel.get('handle') if isinstance(channel, dict) else None
            
            final_response = ProcessedResponse(
                success=True,
                link=extracted_data.text,
                locations=locations,
                author=author,
                name=extracted_data.senderName,
                phoneNo=extracted_data.waId
            )
            
            print("Final API Response:", final_response.model_dump())
            return final_response
            
        except Exception as e:
            return ProcessedResponse(
                success=False,
                link=message.text,
                name=message.senderName,
                phoneNo=message.waId,
                error=f"Error processing message: {str(e)}"
            )
        
content_processor = ContentProcessor() 