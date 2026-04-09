"""Google Maps direct scraper - mimics working tools."""
import asyncio
import json
import re
from typing import List, Optional, Dict
from urllib.parse import quote_plus
import httpx
from models import Business


class GMapsScraper:
    """Scrapes Google Maps directly using the /maps endpoint."""
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxy_list = proxy_list or []
        self.proxy_index = 0
        
    def _get_proxy(self) -> Optional[str]:
        """Get next proxy."""
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    async def scrape(
        self, 
        query: str, 
        location: str, 
        max_results: Optional[int] = None,
        progress_callback = None
    ) -> List[Business]:
        """Scrape Google Maps for businesses."""
        search_term = f"{query} {location}"
        encoded = quote_plus(search_term)
        
        # Try multiple Google Maps URL patterns
        urls = [
            f"https://www.google.com/maps/search/{quote_plus(query)}+{quote_plus(location)}",
            f"https://www.google.com/maps?q={encoded}",
            f"https://www.google.co.uk/maps?q={encoded}",
        ]
        
        businesses = []
        seen = set()
        
        for url in urls:
            if max_results and len(businesses) >= max_results:
                break
                
            if progress_callback:
                progress_callback("status", f"Scraping Google Maps...")
            
            results = await self._fetch_page(url, progress_callback)
            
            for biz in results:
                key = biz.company_name.lower().strip()
                if key and key not in seen:
                    seen.add(key)
                    businesses.append(biz)
                    
                    if progress_callback:
                        progress_callback("business", biz)
                        progress_callback("count", len(businesses))
                    
                    if max_results and len(businesses) >= max_results:
                        break
            
            if businesses:  # If we got results, no need to try other URLs
                break
            
            await asyncio.sleep(1)  # Delay between attempts
        
        return businesses
    
    async def _fetch_page(self, url: str, progress_callback) -> List[Business]:
        """Fetch and parse a Google Maps page."""
        
        # Try without proxy first, then with proxies
        attempts = [None]  # Direct first
        attempts.extend(self.proxy_list[:3])  # Then try 3 proxies
        
        for proxy in attempts:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Referer": "https://www.google.com/",
                }
                
                client_config = {
                    "timeout": 30,
                    "headers": headers,
                    "follow_redirects": True,
                }
                
                if proxy:
                    client_config["proxy"] = proxy
                    if progress_callback:
                        progress_callback("status", f"Using proxy...")
                
                async with httpx.AsyncClient(**client_config) as client:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        results = self._extract_from_js(response.text)
                        if results:
                            return results
                    
                    elif response.status_code == 429:
                        if progress_callback:
                            progress_callback("status", "Rate limited, rotating...")
                        continue
                        
            except Exception as e:
                continue
        
        return []
    
    def _extract_from_js(self, html: str) -> List[Business]:
        """Extract business data from Google's JavaScript embedded in HTML."""
        businesses = []
        
        # Google Maps embeds data in window.APP_INITIALIZATION_STATE or similar
        # Look for JSON-like structures with business data
        
        # Pattern 1: Look for place data in script tags
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'APP_INITIALIZATION_STATE\s*=\s*(\[.+?\]);',
            r'"place\":\s*(\{.+?\})',
            r'data:\s*(\{.+?\"name\".+?\})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches[:5]:  # Limit to first 5 matches
                try:
                    data = json.loads(match)
                    biz = self._parse_business_data(data)
                    if biz:
                        businesses.append(biz)
                except:
                    pass
        
        # Pattern 2: Look for embedded place arrays
        place_pattern = r'"(\d+)\"\s*:\s*\{\s*"(\d+)\"\s*:\s*\[\s*null\s*,\s*"([^"]+)"'
        places = re.findall(place_pattern, html)
        
        for place in places:
            try:
                # Place data often contains name, address, coords
                name = place[2] if len(place) > 2 else None
                if name:
                    businesses.append(Business(company_name=name))
            except:
                pass
        
        # Pattern 3: Simple text extraction from known patterns
        # Look for business names in specific JSON structures
        name_pattern = r'"name":"([^"]{3,100})"'
        website_pattern = r'"website":"(https?://[^"]+)"'
        phone_pattern = r'"phone":"(\+?\d[\d\s\-\(\)]{7,20})"'
        address_pattern = r'"address":"([^"]{10,200})"'
        category_pattern = r'"category":"([^"]{3,50})"'
        
        names = re.findall(name_pattern, html)
        websites = re.findall(website_pattern, html)
        phones = re.findall(phone_pattern, html)
        addresses = re.findall(address_pattern, html)
        categories = re.findall(category_pattern, html)
        
        # Match up the data
        for i, name in enumerate(names[:20]):  # Limit to first 20
            if len(name) > 2:  # Valid name
                biz = Business(company_name=name)
                
                if i < len(websites):
                    biz.website = websites[i]
                if i < len(phones):
                    biz.phone = phones[i]
                if i < len(addresses):
                    biz.address = addresses[i]
                if i < len(categories):
                    biz.category = categories[i]
                
                businesses.append(biz)
        
        return businesses
    
    def _parse_business_data(self, data: Dict) -> Optional[Business]:
        """Parse a business from structured data."""
        try:
            # Try multiple possible structures
            name = None
            
            if isinstance(data, dict):
                # Direct fields
                name = data.get('name') or data.get('title')
                
                # Nested in place data
                if not name and 'place' in data:
                    name = data['place'].get('name')
                
                if name:
                    biz = Business(company_name=str(name))
                    
                    # Get website
                    website = data.get('website') or data.get('url')
                    if website:
                        biz.website = str(website)
                    
                    # Get phone
                    phone = data.get('phone') or data.get('telephone')
                    if phone:
                        biz.phone = str(phone)
                    
                    # Get address
                    address = data.get('address') or data.get('formatted_address')
                    if address:
                        biz.address = str(address)
                    
                    # Get category
                    category = data.get('category') or data.get('type')
                    if category:
                        biz.category = str(category)
                    
                    return biz
                    
        except:
            pass
        
        return None
