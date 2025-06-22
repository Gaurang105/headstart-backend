from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class GlobalLinkDocument(BaseModel):
    """Document model for global_links collection"""
    link: str
    author: Optional[str] = None
    locations: List[Dict[str, Any]] = []
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    processed_count: int = 1

class UserLinkItem(BaseModel):
    """Individual link item in user's links array"""
    url: str
    added_at: datetime = Field(default_factory=datetime.utcnow)

class UserLocationItem(BaseModel):
    """Individual location item in user's locations array"""
    poi_name: str
    category: str
    geo_location: List[float]  # [lat, lng]
    maps_url: str
    website_url: str
    photos_links: List[Dict[str, Any]]
    city: str
    tgid: Optional[str] = None
    source_link: str
    added_at: datetime = Field(default_factory=datetime.utcnow)

class UserDocument(BaseModel):
    """Document model for users collection"""
    name: str
    phoneNo: str
    links: List[UserLinkItem] = []
    locations: List[UserLocationItem] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
