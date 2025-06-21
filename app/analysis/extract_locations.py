import json
from enum import Enum
import openai
from process_google_places import ProcessGooglePlaces


class VideoType(Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram" 
    TIKTOK = "tiktok"
    BLOG = "blog"


class ExtractLocations:
    """
    A class to extract location information from video transcripts using OpenAI API.
    """
    
    def __init__(self, openai_client=None):
        """
        Initialize the ExtractLocations class.
        
        Args:
            openai_client: Optional OpenAI client instance. If not provided, will create one.
        """
        self.client = openai_client or openai.OpenAI()
        
        # Initialize Google Places API (optional - will be None if API key not set)
        try:
            self.google_places = ProcessGooglePlaces()
        except ValueError as e:
            print(f"Warning: Google Places API not available - {e}")
            self.google_places = None

    def send_llm_request(self, transcript_text, timestamps=None, timestamped=False):
        """
        Extract locations from transcript using OpenAI API.
        
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
        
        # Define output format based on timestamped flag
        if timestamped:
            output_format = """
            Provide the output as a valid JSON object in this format:
            {{
                "locations": [
                    {{
                        "name": "Location Name",
                        "timestamp": "MM:SS",
                        "type": "landmark|restaurant|cafe|attraction"
                        "location": "City, Country"
                    }}
                ]
            }}
            """
        else:
            output_format = """
            Provide the output as a valid JSON object in this format:
            {{
                "locations": [
                    {{
                        "name": "Location Name",
                        "type": "landmark|restaurant|cafe|attraction"
                    }}
                ]
            }}
            """
        
        # Complete prompt
        prompt = base_prompt + output_format + """
        Focus on:
        - Landmarks: monuments, temples, historical sites, famous buildings
        - Restaurants/Cafes: dining establishments, food spots, bars
        - Attractions: tourist sites, parks, museums, entertainment venues
        """
        try:
            # Make OpenAI API call
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a travel video analyzer that extracts location information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            # Parse the response
            result = response.choices[0].message.content
            return json.loads(result)
            
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None

    def process_yt(self, data):
        """
        Process YouTube video data to extract locations.
        
        Args:
            data (dict): YouTube video data containing transcript information
            
        Returns:
            dict: Google Places results for extracted locations
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
                        
                        # Combine LLM results with Google Places results
                        combined_results = []
                        for i, location in enumerate(llm_result['locations']):
                            combined_result = {
                                'llm_data': location,
                                'google_places_data': google_places_results[i] if i < len(google_places_results) else None
                            }
                            combined_results.append(combined_result)
                        
                        return {
                            'locations': combined_results,
                            'original_llm_result': llm_result
                        }
                    else:
                        # Fallback to just LLM results if Google Places API not available
                        return {
                            'locations': [{'llm_data': location, 'google_places_data': None} for location in llm_result['locations']],
                            'original_llm_result': llm_result
                        }
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
            dict: Google Places results for extracted locations
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
                    
                    # Combine LLM results with Google Places results
                    combined_results = []
                    for i, location in enumerate(llm_result['locations']):
                        combined_result = {
                            'llm_data': location,
                            'google_places_data': google_places_results[i] if i < len(google_places_results) else None
                        }
                        combined_results.append(combined_result)
                    
                    return {
                        'locations': combined_results,
                        'original_llm_result': llm_result
                    }
                else:
                    # Fallback to just LLM results if Google Places API not available
                    return {
                        'locations': [{'llm_data': location, 'google_places_data': None} for location in llm_result['locations']],
                        'original_llm_result': llm_result
                    }
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
    
    # Path to the JSON file
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