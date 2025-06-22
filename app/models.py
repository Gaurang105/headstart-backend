from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class WhatsAppMessage(BaseModel):
    # Essential fields - always required
    text: str
    waId: str
    senderName: str
    
    # Optional fields from full WhatsApp bot payload
    id: Optional[str] = None
    created: Optional[str] = None
    whatsappMessageId: Optional[str] = None
    conversationId: Optional[str] = None
    ticketId: Optional[str] = None
    type: Optional[str] = None
    data: Optional[Any] = None
    sourceId: Optional[str] = None
    sourceUrl: Optional[str] = None
    timestamp: Optional[str] = None
    owner: Optional[bool] = None
    eventType: Optional[str] = None
    statusString: Optional[str] = None
    avatarUrl: Optional[str] = None
    assignedId: Optional[str] = None
    operatorName: Optional[str] = None
    operatorEmail: Optional[str] = None
    messageContact: Optional[Any] = None
    listReply: Optional[Any] = None
    interactiveButtonReply: Optional[Any] = None
    buttonReply: Optional[Any] = None
    replyContextId: Optional[str] = None
    sourceType: Optional[int] = None
    frequentlyForwarded: Optional[bool] = None
    forwarded: Optional[bool] = None


class ExtractedData(BaseModel):
    waId: str
    senderName: str
    text: str
    platform: str  # 'youtube' or 'instagram'


class YouTubeChannel(BaseModel):
    id: str
    url: str
    handle: str
    title: str


class YouTubeVideo(BaseModel):
    id: str
    title: str
    thumbnail: str
    channel: YouTubeChannel
    publishDateText: str
    publishDate: str
    viewCountText: str
    viewCountInt: int
    lengthText: Optional[str] = None
    videoUrl: str


class TranscriptItem(BaseModel):
    text: str
    startMs: str
    endMs: str
    startTimeText: str


class YouTubeResponse(BaseModel):
    id: str
    thumbnail: Optional[str] = None
    type: str
    title: str
    description: Optional[str] = None
    commentCountText: Optional[str] = None
    commentCountInt: Optional[int] = None
    likeCountText: Optional[str] = None
    likeCountInt: Optional[int] = None
    viewCountText: Optional[str] = None
    viewCountInt: Optional[int] = None
    publishDateText: Optional[str] = None
    publishDate: Optional[str] = None
    channel: YouTubeChannel
    watchNextVideos: Optional[List[YouTubeVideo]] = []
    transcript: Optional[List[TranscriptItem]] = []
    transcript_only_text: Optional[str] = None


class InstagramTranscript(BaseModel):
    id: str
    shortcode: str
    text: str


class InstagramResponse(BaseModel):
    success: bool
    transcripts: List[InstagramTranscript]


class LocationData(BaseModel):
    poi_name: str
    category: str
    geo_location: List[float]  # [lng, lat] for MongoDB 2dsphere compatibility
    maps_url: str
    website_url: str
    photos_links: List[Dict[str, Any]]
    city: str
    tgid: Optional[str] = None


class ProcessedResponse(BaseModel):
    success: bool
    link: str
    locations: Optional[List[LocationData]] = None
    author: Optional[str] = None
    name: str
    phoneNo: str
    error: Optional[str] = None


class LoginRequest(BaseModel):
    name: str
    phoneNo: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user_exists: bool
    name: str
    phoneNo: str
    error: Optional[str] = None


class GetCitiesRequest(BaseModel):
    phoneNo: str


class GetCitiesResponse(BaseModel):
    success: bool
    phoneNo: str
    cities: List[str]
    total_cities: int
    message: str
    error: Optional[str] = None


class GetPoisRequest(BaseModel):
    phoneNo: str


class PoiData(BaseModel):
    poi_name: str
    category: str
    geo_location: List[float]  # [lng, lat] for MongoDB 2dsphere compatibility
    maps_url: str
    website_url: str
    photos_links: List[Dict[str, Any]]
    city: str
    tgid: Optional[str] = None
    source_link: str
    added_at: str  # ISO datetime string


class GetPoisResponse(BaseModel):
    success: bool
    phoneNo: str
    pois: List[PoiData]
    total_pois: int
    message: str
    error: Optional[str] = None


class GetLinksRequest(BaseModel):
    phoneNo: str


class LinkData(BaseModel):
    url: str
    added_at: str  # ISO datetime string


class GetLinksResponse(BaseModel):
    success: bool
    phoneNo: str
    links: List[LinkData]
    total_links: int
    message: str
    error: Optional[str] = None 