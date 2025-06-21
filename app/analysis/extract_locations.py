import json
from enum import Enum
from typing import List, Optional
import google.generativeai as genai
from process_google_places import ProcessGooglePlaces
import os


class VideoType(Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram" 
    TIKTOK = "tiktok"
    BLOG = "blog"

possible_categories = ["Eats", "Attractions", "Stay", "Shopping", "Nature & Parks", "Hidden Gems", "Nightlife"]

category_descriptions = """Here’s what each category means:

- Eats: Any location primarily focused on food or drink. Includes restaurants, cafes, food stalls, dessert
  shops, street food spots, breweries, or places known for a signature dish or culinary experience.

- Attractions: Well-known or iconic places that people visit for sightseeing or experiences. This includes
  museums, monuments, theme parks, cultural landmarks, observation decks, and major tourist sites.

- Stay: Any type of accommodation where someone might spend the night. Includes hotels, hostels, resorts,
  vacation rentals, guesthouses, and unique stays like treehouses, boats, or homestays.

- Shopping: Locations focused on retail or local goods. Includes malls, markets, shopping streets, boutiques,
  souvenir shops, artisan stores, and specialty food stores.

- Nature & Parks: Outdoor locations with natural beauty or green space. Includes national parks, beaches,
  hiking trails, lakes, gardens, forests, mountains, and scenic viewpoints.

- Hidden Gems: Lesser-known or off-the-beaten-path places that are not crowded or widely publicized. Often
  local favorites or secret spots that feel special, authentic, or uniquely charming.

- Nightlife: Places known for activity after dark. Includes bars, clubs, night markets, late-night food spots,
  live music venues, lounges, and any social venue that thrives at night."""

class ExtractLocations:
    """
    A class to extract location information from video transcripts using Google Gemini API.
    """
    
    def __init__(self, gemini_client=None):
        """
        Initialize the ExtractLocations class.
        
        Args:
            gemini_client: Optional Gemini client instance. If not provided, will create one.
        """
        if gemini_client:
            self.client = gemini_client
        else:
            # Initialize Gemini client (you'll need to set GOOGLE_API_KEY environment variable)
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            self.client = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize Google Places API (optional - will be None if API key not set)
        try:
            self.google_places = ProcessGooglePlaces()
        except ValueError as e:
            print(f"Warning: Google Places API not available - {e}")
            self.google_places = None

    def send_llm_request(self, transcript_text, timestamps=None, timestamped=False):
        """
        Extract locations from transcript using Google Gemini API with structured response.
        
        Args:
            transcript_text (str): Full transcript text
            timestamps (list, optional): List of timestamped transcript segments
            timestamped (bool): Whether to include timestamps in the output
            
        Returns:
            dict: Extracted locations with optional timestamps
        """
        
        # Base prompt
        base_prompt = f"""
        Extract all location names, landmarks, restaurants, cafes, and 
        attractions from this travel video transcript.  Do not add city, 
        state/province or country names as a seperate location.
        Try to get to the core location name and not just a description. 
        These locations will be used to geocode the locations. 
        So make sure to extract the core location name.

        For example, if the transcript says "Greenwich Meridian Line at the Royal Observatory", 
        the location name should just be "Royal Observatory".

        Also watch out for brand names and locations that might be duplicated. 

        For example, if the transcript says, "I love everything about the citizen M hotels especially their Tower of London hotel"
        the location name should just be "Citizen M Tower of London"

        Extract only the name of the location that this person seems to be visiting, 
        add any neighborhood or related landmark information to the main location name. 

        For example, if the transcript says, "I went to the shoreditch neighborhood to get to Dishoom"
        the location name should be "Dishoom Shoreditch"

        Finally, make a best guess as to the city and country of the location (for each location) and add it to the result as in 
        structure given below
        
        Full transcript: {transcript_text}
        """
        
        # Add timestamp information if provided
        if timestamped and timestamps:
            base_prompt += f"\nTimestamped segments: {timestamps}\n"
            base_prompt += "\nUse the timestamp information provided to match locations with their timestamps."
        
        # Complete prompt
        prompt = base_prompt + """
        Focus on:
        - Landmarks: monuments, temples, historical sites, famous buildings
        - Restaurants/Cafes: dining establishments, food spots, bars
        - Attractions: tourist sites, parks, museums, entertainment venues
        """
        
        try:
            # Define schema based on whether timestamps are needed
            if timestamped:
                response_schema = {
                    "type": "object",
                    "properties": {
                        "locations": {
                            "type": "array",
                            "description": "List of locations found in the video transcript",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "The specific name of the location, landmark, restaurant, or attraction"
                                    },
                                    "type": {
                                        "type": "string", 
                                        "enum": possible_categories,
                                        "description": category_descriptions
                                    }, 
                                    "location": {
                                        "type": "string",
                                        "description": "City and country where this location is situated (e.g., 'London, UK', 'Paris, France')"
                                    },
                                    "timestamp": {
                                        "type": "string",
                                        "description": "Timestamp in MM:SS format when this location is mentioned in the video"
                                    }
                                },
                                "required": ["name", "type", "location", "timestamp"]
                            }
                        }
                    },
                    "required": ["locations"]
                }
            else:
                response_schema = {
                    "type": "object",
                    "properties": {
                        "locations": {
                            "type": "array",
                            "description": "List of locations found in the video transcript",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "The specific name of the location, landmark, restaurant, or attraction"
                                    },
                                    "type": {
                                        "type": "string", 
                                        "enum": possible_categories,
                                        "description": category_descriptions
                                    }, 
                                    "location": {
                                        "type": "string",
                                        "description": "City and country where this location is situated (e.g., 'London, UK', 'Paris, France')"
                                    }
                                },
                                "required": ["name", "type", "location"]
                            }
                        }
                    },
                    "required": ["locations"]
                }
            
            # Configure generation with structured response
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=response_schema
            )
            
            # Make Gemini API call with structured response
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Parse the response
            result_json = response.text
            result = json.loads(result_json)
            return result
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return None

    def _process_location_results(self, llm_result, google_places_results):
        """
        Process and combine LLM results with Google Places data.
        
        Args:
            llm_result (dict): Results from LLM extraction
            google_places_results (list): Results from Google Places API
            
        Returns:
            list: Processed location results with combined data
        """
        if not llm_result or 'locations' not in llm_result:
            return []
            
        final_results = []
        for i, location in enumerate(llm_result['locations']):
            # Get the google places data
            google_places_data = google_places_results[i] if i < len(google_places_results) else None
            
            # Get the name of the location
            name = location.get('name', 'Unknown')
            type = location.get('type', 'Hidden Gems')
            city = location.get('location', 'Unknown')
            coordinates = [0.0, 0.0]
            
            place_details = google_places_data.get('details', {}) if google_places_data else {}
            
            if place_details:
                coordinates = place_details.get('coordinates', [0.0, 0.0])
                maps_url = place_details.get('google_maps_url', 'Unknown')
                website_url = place_details.get('website', 'Unknown')
                photos_links = place_details.get('photos', [])
            else:
                maps_url = 'Unknown'
                website_url = 'Unknown'
                photos_links = []

            result = {
                'poi_name': name, 
                'category': type, 
                'geo_location': coordinates,
                'maps_url': maps_url,
                'website_url': website_url,
                'photos_links': photos_links,
                'city': city,
                'tgid': None
            }
            final_results.append(result)
            
        return final_results

    def process_yt(self, data):
        """
        Process YouTube video data to extract locations.
        
        Args:
            data (dict): YouTube video data containing transcript information
            
        Returns:
            list: Processed location results
        """
        try:
            # Extract the transcript_only_text field
            transcript_text = data.get('transcript_only_text')
            
            # Extract the timestamped transcript
            transcript_timestamps = data.get('transcript', [])
            
            if transcript_text and transcript_timestamps:            
                # Convert timestamped transcript to a more usable format
                timestamps = []
                for entry in transcript_timestamps:
                    timestamps.append({
                        'text': entry.get('text', ''),
                        'startTimeText': entry.get('startTimeText', '')
                    })
                
                # Get locations from LLM
                llm_result = self.send_llm_request(transcript_text, timestamps, timestamped=True)
                
                if llm_result and 'locations' in llm_result:
                    # Extract location strings from LLM result
                    location_strings = [location['name'] for location in llm_result['locations']]
                    
                    # Get Google Places details for each location (if available)
                    if self.google_places:
                        google_places_results = self.google_places.get_google_places(location_strings)
                        return self._process_location_results(llm_result, google_places_results)
                    else:
                        # Fallback to just LLM results if Google Places API not available
                        return self._process_location_results(llm_result, [])
                else:
                    print("No locations found in LLM response.")
                    return None
            else:
                print("No transcript data found in the JSON file.")
                return None
                
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON format - {e}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def process_reels(self, data):
        """
        Process Instagram Reels data to extract locations.
        
        Args:
            data (dict): Instagram Reels data containing transcript information
            
        Returns:
            list: Processed location results
        """
        try:
            # Extract the transcript_only_text field
            transcript_text = data.get('transcripts')[0].get('text')
            
            # Get locations from LLM
            llm_result = self.send_llm_request(transcript_text, timestamped=False)
            
            if llm_result and 'locations' in llm_result:
                # Extract location strings from LLM result
                location_strings = [location['name'] for location in llm_result['locations']]
                
                # Get Google Places details for each location (if available)
                if self.google_places:
                    google_places_results = self.google_places.get_google_places(location_strings)
                    return self._process_location_results(llm_result, google_places_results)
                else:
                    # Fallback to just LLM results if Google Places API not available
                    return self._process_location_results(llm_result, [])
            else:
                print("No locations found in LLM response.")
                return None
                
        except Exception as e:
            print(f"Error: {e}")
            return None

    def extract_transcript_text_tiktok(self, data):
        """
        Extract transcript text from TikTok data.
        
        Args:
            data (dict): TikTok video data
            
        Returns:
            dict: Extracted locations (currently returns None as not implemented)
        """
        return None

    def extract_locations(self, data, video_type):
        """
        Main method to extract locations from video data based on video type.
        
        Args:
            data (dict): Video data containing transcript information
            video_type (VideoType): Type of video (YouTube, Instagram, TikTok, etc.)
            
        Returns:
            dict: Extracted locations
        """ 
        if video_type == VideoType.YOUTUBE:
            return self.process_yt(data)
        elif video_type == VideoType.INSTAGRAM:
            return self.process_reels(data)
        elif video_type == VideoType.TIKTOK:
            return self.extract_transcript_text_tiktok(data)
        else:
            print(f"Unsupported video type: {video_type}")
            return None


if __name__ == "__main__":
    # Create an instance of ExtractLocations
    extractor = ExtractLocations()
    
    #Path to the JSON file
    # json_file = "tests/youtube.json"
    # with open(json_file, 'r', encoding='utf-8') as file:
    #     data = json.load(file)
    
    # # Extract and print the transcript
    # locations = extractor.extract_locations(data, VideoType.YOUTUBE) 

    json_file = "tests/reel.json"
    with open(json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Extract and print the transcript
    locations = extractor.extract_locations(data, VideoType.INSTAGRAM) 

    print(locations)