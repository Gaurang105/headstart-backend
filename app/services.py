import httpx
import re
from typing import Optional

from app.config import settings
from app.models import (
    WhatsAppMessage, 
    ExtractedData, 
    YouTubeResponse, 
    InstagramResponse,
    ProcessedResponse
)


class ContentProcessor:
    """Service class for processing WhatsApp messages and fetching content data."""
    
    def __init__(self):
        self.youtube_api_url = settings.YOUTUBE_API_URL
        self.instagram_api_url = settings.INSTAGRAM_API_URL
        self.api_key = settings.SCRAPE_CREATORS_API_KEY
        self.timeout = settings.REQUEST_TIMEOUT
    
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
    
    async def process_message(self, message: WhatsAppMessage) -> ProcessedResponse:
        try:
            extracted_data = self.extract_data_from_message(message)
            
            if extracted_data.platform == 'unknown':
                return ProcessedResponse(
                    success=False,
                    platform='unknown',
                    extracted_data=extracted_data,
                    error="URL platform not supported. Only YouTube and Instagram are supported."
                )
            
            content_data = None
            if extracted_data.platform == 'youtube':
                youtube_data = await self.fetch_youtube_data(extracted_data.text)
                if youtube_data:
                    content_data = youtube_data.model_dump()
                else:
                    return ProcessedResponse(
                        success=False,
                        platform=extracted_data.platform,
                        extracted_data=extracted_data,
                        error="Failed to fetch YouTube data"
                    )
            
            elif extracted_data.platform == 'instagram':
                instagram_data = await self.fetch_instagram_data(extracted_data.text)
                if instagram_data:
                    content_data = instagram_data.model_dump()
                else:
                    return ProcessedResponse(
                        success=False,
                        platform=extracted_data.platform,
                        extracted_data=extracted_data,
                        error="Failed to fetch Instagram data"
                    )
            
            return ProcessedResponse(
                success=True,
                platform=extracted_data.platform,
                extracted_data=extracted_data,
                content_data=content_data
            )
            
        except Exception as e:
            return ProcessedResponse(
                success=False,
                platform='unknown',
                extracted_data=ExtractedData(
                    waId=message.waId,
                    senderName=message.senderName,
                    text=message.text,
                    platform='unknown'
                ),
                error=f"Error processing message: {str(e)}"
            )
        
content_processor = ContentProcessor() 