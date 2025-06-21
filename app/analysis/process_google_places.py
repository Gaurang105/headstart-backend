import googlemaps
from app.config import settings

class ProcessGooglePlaces:
    def __init__(self):
        """Initialize the ProcessGooglePlaces class."""
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        if not self.api_key:
            raise ValueError('GOOGLE_MAPS_API_KEY environment variable not set')
        self.gmaps = googlemaps.Client(key=self.api_key)
    
    def _get_place_details(self, place_string):
        try:
            # Geocode the place
            geocode_result = self.gmaps.geocode(place_string)
            
            if geocode_result:
                # Get the first result
                location = geocode_result[0]['geometry']['location']
                place_id = geocode_result[0].get('place_id')
                
                # Get detailed information using Places API
                if place_id:
                    try:
                        # Get place details including photos
                        place_details_result = self.gmaps.place(
                            place_id,
                            fields=['name', 'formatted_address', 'photo', 'url', 'website', 'rating', 'user_ratings_total']
                        )
                        
                        if place_details_result.get('status') == 'OK':
                            result = place_details_result['result']
                            
                            # Extract photo information
                            photos = []
                            if 'photo' in result:
                                for photo in result['photo'][:3]:  # Limit to first 3 photos
                                    photo_ref = photo.get('photo_reference')
                                    if photo_ref:
                                        # Generate photo URL
                                        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={self.api_key}"
                                        photos.append({
                                            'photo_reference': photo_ref,
                                            'url': photo_url,
                                            'width': photo.get('width'),
                                            'height': photo.get('height')
                                        })
                            
                            # Store all information
                            place_info = {
                                'coordinates': (location['lat'], location['lng']),
                                'place_id': place_id,
                                'name': result.get('name', 'Unknown'),
                                'formatted_address': result.get('formatted_address', 'Unknown'),
                                'google_maps_url': result.get('url', 'Unknown'),
                                'website': result.get('website', 'Unknown'),
                                'rating': result.get('rating', 'Unknown'),
                                'user_ratings_total': result.get('user_ratings_total', 'Unknown'),
                                'photos': photos
                            }
                            
                            return place_info
                            
                        else:
                            error_msg = f"Places API error: {place_details_result.get('status')}"
                            return {
                                'coordinates': (location['lat'], location['lng']),
                                'place_id': place_id,
                                'error': error_msg
                            }
                            
                    except Exception as e:
                        error_msg = f"Place details error: {str(e)}"
                        return {
                            'coordinates': (location['lat'], location['lng']),
                            'place_id': place_id,
                            'error': error_msg
                        }
                else:
                    error_msg = 'No place ID available'
                    return {
                        'coordinates': (location['lat'], location['lng']),
                        'error': error_msg
                    }
            else:
                return None
                
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            return {'error': error_msg}

    def get_google_places(self, places_array):
        results = []
        
        for place in places_array:
            details = self._get_place_details(place)
            results.append({
                'place_string': place,
                'details': details
            })
        
        return results

    def print_place_details(self, place_string, details):
        print(f"\n{place_string}")
        if details is None:
            print("No results found")
        elif 'error' in details:
            print(f"Error: {details['error']}")
        else:
            print(f"Name: {details['name']}")
            print(f"Coordinates: {details['coordinates']}")
            print(f"Address: {details['formatted_address']}")
            print(f"Google Maps: {details['google_maps_url']}")
            if details['website'] != 'Unknown':
                print(f"Website: {details['website']}")
            if details['rating'] != 'Unknown':
                print(f"Rating: {details['rating']} ({details['user_ratings_total']} reviews)")
            if details['photos']:
                print(f"Photos: {len(details['photos'])} available")
                for i, photo in enumerate(details['photos'][:2], 1):  # Show first 2 photos
                    print(f"Photo {i}: {photo['url']}")