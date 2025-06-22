from typing import Optional
import httpx

class HeadoutIntegration:
    """
    A class to handle integration with Headout's search API.
    """
    
    def __init__(self, base_url: str = "https://search.headout.com/api/v3/search/"):
        """
        Initialize the Headout integration.
        
        Args:
            base_url: The base URL for the Headout search API
        """
        self.base_url = base_url
    
    async def search_headout_products(self, city: str, poi_name: str) -> Optional[int]:
        """
        Search for products on Headout using city and POI name.
        
        Args:
            city: The city name
            poi_name: The point of interest name
            
        Returns:
            ID of the first product result or None if failed
        """
        try:
            # Create search query by combining city and POI name
            query = f"{city}+{poi_name}".replace(' ', '+')
            
            # Construct the search URL
            url = f"{self.base_url}?query={query}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                search_data = response.json()
                
                # Parse the results to find the first product ID
                results = search_data.get('results', [])
                
                for result in results:
                    if result.get('type') == 'PRODUCT':
                        values = result.get('values', [])
                        if values:
                            first_product_id = values[0].get('id')
                            return str(first_product_id) if first_product_id is not None else None
                
                return None
                
        except httpx.HTTPError as e:
            return None
        except Exception as e:
            return None