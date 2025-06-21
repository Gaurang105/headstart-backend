from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class WhatsAppMessage(BaseModel):
    id: str
    created: str
    whatsappMessageId: str
    conversationId: str
    ticketId: str
    text: str
    type: str
    data: Optional[Any] = None
    sourceId: Optional[str] = None
    sourceUrl: Optional[str] = None
    timestamp: str
    owner: bool
    eventType: str
    statusString: str
    avatarUrl: Optional[str] = None
    assignedId: Optional[str] = None
    operatorName: Optional[str] = None
    operatorEmail: Optional[str] = None
    waId: str
    messageContact: Optional[Any] = None
    senderName: str
    listReply: Optional[Any] = None
    interactiveButtonReply: Optional[Any] = None
    buttonReply: Optional[Any] = None
    replyContextId: str
    sourceType: int
    frequentlyForwarded: bool
    forwarded: bool


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
    thumbnail: str
    type: str
    title: str
    description: str
    commentCountText: str
    commentCountInt: int
    likeCountText: str
    likeCountInt: int
    viewCountText: str
    viewCountInt: int
    publishDateText: str
    publishDate: str
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


class ProcessedResponse(BaseModel):
    success: bool
    platform: str
    extracted_data: ExtractedData
    content_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None 