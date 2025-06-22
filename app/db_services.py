from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.database import get_global_collection, get_users_collection
from app.db_models import GlobalLinkDocument, UserDocument, UserLinkItem, UserLocationItem

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service class for database operations"""
    
    def __init__(self):
        self._global_collection = None
        self._users_collection = None
    
    @property
    def global_collection(self):
        """Lazy-load global collection"""
        if self._global_collection is None:
            self._global_collection = get_global_collection()
        return self._global_collection
    
    @property
    def users_collection(self):
        """Lazy-load users collection"""
        if self._users_collection is None:
            self._users_collection = get_users_collection()
        return self._users_collection
    
    async def get_global_link_data(self, link: str) -> Optional[Dict[str, Any]]:
        """Get data for a link from global collection"""
        try:
            result = await self.global_collection.find_one({"link": link})
            if result:
                logger.info(f"Found existing link in global collection: {link}")
            return result
        except Exception as e:
            logger.error(f"Error fetching global link data: {e}")
            return None
    
    async def save_global_link_data(self, link: str, author: Optional[str], locations: List[Dict[str, Any]]) -> bool:
        """Save link data to global collection"""
        try:
            doc = GlobalLinkDocument(
                link=link,
                author=author,
                locations=locations,
                processed_at=datetime.utcnow(),
                processed_count=1
            )
            
            result = await self.global_collection.insert_one(doc.model_dump())
            logger.info(f"Saved new link to global collection: {link}")
            return result.inserted_id is not None
        except Exception as e:
            logger.error(f"Error saving global link data: {e}")
            return False
    
    async def increment_processed_count(self, link: str) -> bool:
        """Increment processed count for existing link"""
        try:
            result = await self.global_collection.update_one(
                {"link": link},
                {"$inc": {"processed_count": 1}}
            )
            logger.info(f"Incremented processed count for link: {link}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error incrementing processed count: {e}")
            return False
    
    async def get_user_data(self, phone_no: str) -> Optional[Dict[str, Any]]:
        """Get user data by phone number"""
        try:
            result = await self.users_collection.find_one({"phoneNo": phone_no})
            return result
        except Exception as e:
            logger.error(f"Error fetching user data: {e}")
            return None
    
    async def create_user(self, name: str, phone_no: str) -> bool:
        """Create new user"""
        try:
            doc = UserDocument(
                name=name,
                phoneNo=phone_no,
                links=[],
                locations=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            result = await self.users_collection.insert_one(doc.model_dump())
            logger.info(f"Created new user: {name} ({phone_no})")
            return result.inserted_id is not None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    async def add_link_to_user(self, phone_no: str, link: str) -> bool:
        """Add link to user's links array if not already exists"""
        try:
            # Check if link already exists for this user
            existing_user = await self.users_collection.find_one({
                "phoneNo": phone_no,
                "links.url": link
            })
            
            if existing_user:
                logger.info(f"Link already exists for user {phone_no}: {link}")
                return True
            
            # Add new link
            new_link = UserLinkItem(url=link, added_at=datetime.utcnow())
            result = await self.users_collection.update_one(
                {"phoneNo": phone_no},
                {
                    "$push": {"links": new_link.model_dump()},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            logger.info(f"Added link to user {phone_no}: {link}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding link to user: {e}")
            return False
    
    async def add_locations_to_user(self, phone_no: str, locations: List[Dict[str, Any]], source_link: str) -> bool:
        """Add locations to user's locations array"""
        try:
            # Convert to UserLocationItem format
            user_locations = []
            for loc in locations:
                user_location = UserLocationItem(
                    poi_name=loc.get('poi_name', ''),
                    category=loc.get('category', ''),
                    geo_location=loc.get('geo_location', [0.0, 0.0]),
                    maps_url=loc.get('maps_url', ''),
                    website_url=loc.get('website_url', ''),
                    photos_links=loc.get('photos_links', []),
                    city=loc.get('city', ''),
                    tgid=loc.get('tgid'),
                    source_link=source_link,
                    added_at=datetime.utcnow()
                )
                user_locations.append(user_location.model_dump())
            
            if user_locations:
                result = await self.users_collection.update_one(
                    {"phoneNo": phone_no},
                    {
                        "$push": {"locations": {"$each": user_locations}},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
                
                logger.info(f"Added {len(user_locations)} locations to user {phone_no}")
                return result.modified_count > 0
            
            return True
        except Exception as e:
            logger.error(f"Error adding locations to user: {e}")
            return False
    
    async def update_user_data(self, phone_no: str, name: str, link: str, locations: List[Dict[str, Any]]) -> bool:
        """Update user data with new link and locations"""
        try:
            # Get or create user
            user = await self.get_user_data(phone_no)
            if not user:
                await self.create_user(name, phone_no)
            
            # Add link to user
            await self.add_link_to_user(phone_no, link)
            
            # Add locations to user (only those with valid coordinates)
            valid_locations = [loc for loc in locations if loc.get('geo_location') != [0.0, 0.0]]
            if valid_locations:
                await self.add_locations_to_user(phone_no, valid_locations, link)
            
            return True
        except Exception as e:
            logger.error(f"Error updating user data: {e}")
            return False

# Create singleton instance
db_service = DatabaseService()
