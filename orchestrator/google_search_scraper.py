"""Fast Google Search scraper for business listings."""
import asyncio
import re
from typing import List, Optional
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup
from models import Business


class GoogleSearchScraper:
    """Fast scraper using Google Search (not Maps directly)."""
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxy_list = proxy_list or []
        self.proxy_index = 0
        
    def _get_next_proxy(self) -> Optional[str]:
        """Get next proxy in rotation."""
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
        """Scrape Google Search for businesses."""
        businesses = []
        seen_names = set()
        
        search_query = f"{query} {location}"
        start = 0
        
        while True:
            if max_results and len(businesses) >= max_results:
                break
                
            # Fetch search results page
            page_results = await self._fetch_search_page(search_query, start, progress_callback)
            
            if not page_results:
                break
            
            for business in page_results:
                if business.company_name not in seen_names:
                    seen_names.add(business.company_name)
                    businesses.append(business)
                    
                    if progress_callback:
                        progress_callback("business", business)
                        progress_callback("count", len(businesses))
                    
                    if max_results and len(businesses) >= max_results:
                        break
            
            # Check if we got results
            if len(page_results) == 0:
                break
                
            start += 10  # Next page
            await asyncio.sleep(0.5)  # Small delay between pages
        
        return businesses
    
    async def _fetch_search_page(
        self, 
        query: str, 
        start: int,
        progress_callback
    ) -> List[Business]:
        """Fetch a single Google search results page."""
        
        # Construct URL - use local Google to avoid blocks
        encoded_query = quote_plus(query)
        urls = [
            f"https://www.google.com/search?q={encoded_query}&start={start}&num=10",
            f"https://www.google.co.uk/search?q={encoded_query}&start={start}&num=10",
            f"https://www.google.ca/search?q={encoded_query}&start={start}&num=10",
        ]
        
        if progress_callback:
            progress_callback("status", f"Fetching results {start+1}-{start+10}...")
        
        # Try without proxy first, then with proxies
        attempts = [(None, url) for url in urls]
        
        # Add proxy attempts (max 5)
        for proxy in self.proxy_list[:5]:
            attempts.append((proxy, urls[0]))
        
        last_error = None
        
        for proxy, url in attempts:
            try:
                if progress_callback:
                    if proxy:
                        progress_callback("status", f"Trying with proxy...")
                    else:
                        progress_callback("status", f"Direct connection...")
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Cache-Control": "max-age=0",
                }
                
                client_config = {
                    "timeout": 30,
                    "headers": headers,
                    "follow_redirects": True,
                }
                
                if proxy:
                    client_config["proxy"] = proxy
                
                async with httpx.AsyncClient(**client_config) as client:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        results = self._parse_search_results(response.text, progress_callback)
                        if results:
                            return results
                        # Got 200 but no results, might be blocked
                        continue
                    elif response.status_code == 429:
                        if progress_callback:
                            progress_callback("status", f"Rate limited, trying proxy...")
                        continue
                    else:
                        last_error = f"HTTP {response.status_code}"
                        continue
                        
            except Exception as e:
                last_error = str(e)
                continue
        
        if progress_callback:
            progress_callback("status", f"Failed: {last_error[:50] if last_error else 'Unknown'}")
        return []
    
    def _parse_search_results(self, html: str, progress_callback) -> List[Business]:
        """Parse Google search results HTML."""
        businesses = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Check for blocking/captcha
        if any(x in html.lower() for x in ['captcha', 'unusual traffic', 'confirm you', 'i\'m not a robot']):
            if progress_callback:
                progress_callback("status", "Google blocking detected (captcha)")
            return []
        
        # Check for no results
        if 'did not match any documents' in html.lower() or soup.find(text=re.compile(r'no results found', re.I)):
            if progress_callback:
                progress_callback("status", "No results found for query")
            return []
        
        # Look for business listings in various formats
        
        # 1. Local business cards (knowledge panels)
        business_cards = soup.find_all('div', class_=re.compile(r'g|tu-au|VkpGBb|Z1hOCe'))
        
        # 2. Regular search results with business info
        search_results = soup.find_all('div', class_='g')
        
        # 3. Try to find any div with business-like content
        all_results = business_cards + search_results
        
        for result in all_results:
            try:
                business = self._extract_business_from_result(result)
                if business and business.company_name:
                    businesses.append(business)
            except:
                continue
        
        return businesses
    
    def _extract_business_from_result(self, result) -> Optional[Business]:
        """Extract business data from a search result."""
        business = Business()
        
        # Try multiple selectors for name
        name_selectors = [
            'h3',
            '.LC20lb',
            '.DKV0Md',
            '.dbg0pd',
            'h3.LC20lb',
            '[data-attrid="title"]'
        ]
        
        for selector in name_selectors:
            elem = result.select_one(selector)
            if elem:
                name = elem.get_text(strip=True)
                if name and len(name) > 2:
                    business.company_name = name
                    break
        
        if not business.company_name:
            # Try any heading
            headings = result.find_all(['h3', 'h2', 'h1'])
            for h in headings:
                name = h.get_text(strip=True)
                if name and len(name) > 2:
                    business.company_name = name
                    break
        
        # Try to get website
        link_selectors = [
            'a[href^="http"]',
            '.yuRUbf a',
            'a[data-ved]'
        ]
        
        for selector in link_selectors:
            link = result.select_one(selector)
            if link:
                href = link.get('href', '')
                if href and not href.startswith('/'):
                    # Clean the URL
                    if 'url?q=' in href:
                        match = re.search(r'url\?q=([^&]+)', href)
                        if match:
                            business.website = match.group(1)
                    else:
                        business.website = href
                    break
        
        # Try to get category/description
        desc_selectors = [
            '.VwiC3b',
            '.s3v94d',
            '.YyxmKb',
            '.yXK7lf'
        ]
        
        for selector in desc_selectors:
            elem = result.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if text:
                    # Often contains category info
                    business.category = text[:100]  # Truncate long descriptions
                    break
        
        return business if business.company_name else None
