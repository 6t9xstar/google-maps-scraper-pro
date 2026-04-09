"""Google Maps scraper - extracts from sidebar search results feed."""
import asyncio
import re
from typing import List, Optional
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
from models import Business


class GMapsSidebarScraper:
    """Scrapes Google Maps sidebar search results."""
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxy_list = proxy_list or []
        self.proxy_index = 0
        
    def _get_proxy(self) -> Optional[str]:
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    async def _get_working_proxies(self, proxy_list: List[str], max_check: int = 10) -> List[str]:
        """Quickly test proxies and return only working ones."""
        working = []
        test_url = "http://httpbin.org/ip"
        
        async def test_proxy(proxy: str) -> bool:
            try:
                async with httpx.AsyncClient(proxy=proxy, timeout=5) as client:
                    response = await client.get(test_url)
                    return response.status_code == 200
            except:
                return False
        
        # Test first N proxies concurrently
        check_list = proxy_list[:max_check]
        tasks = [test_proxy(p) for p in check_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for proxy, result in zip(check_list, results):
            if result is True:
                working.append(proxy)
        
        return working
    
    async def scrape(
        self, 
        query: str, 
        location: str, 
        max_results: Optional[int] = None,
        progress_callback = None
    ) -> List[Business]:
        """Scrape Google Maps sidebar results."""
        search_term = f"{query} in {location}"
        
        # Filter to working proxies only (test first 10)
        if self.proxy_list and len(self.proxy_list) > 0:
            if progress_callback:
                progress_callback("status", f"Testing {min(10, len(self.proxy_list))} proxies for speed...")
            
            import httpx
            working_proxies = await self._get_working_proxies(self.proxy_list, max_check=10)
            
            if progress_callback:
                progress_callback("status", f"Found {len(working_proxies)} fast proxies")
            
            # Use only working proxies, or empty list for direct connection
            self.proxy_list = working_proxies
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            try:
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                
                page = await context.new_page()
                
                # Navigate to Google Maps with search
                url = f"https://www.google.com/maps/search/{quote_plus(query)}+{quote_plus(location)}"
                
                if progress_callback:
                    progress_callback("status", f"Loading Google Maps (timeout 30s)...")
                
                # Reduced timeout and simpler wait condition
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(3)  # Give time for JS to render
                except Exception as e:
                    if progress_callback:
                        progress_callback("status", f"Load timeout, trying simpler wait...")
                    await page.goto(url, timeout=30000)
                    await asyncio.sleep(5)
                
                if progress_callback:
                    progress_callback("status", f"Extracting results...")
                
                # Extract from sidebar
                businesses = await self._extract_sidebar_results(page, max_results, progress_callback)
                
                await context.close()
                return businesses
                
            finally:
                await browser.close()
    
    async def _extract_sidebar_results(self, page, max_results, progress_callback) -> List[Business]:
        """Extract business data from the sidebar results panel."""
        businesses = []
        seen = set()
        
        # Get all text content from the page and parse business blocks
        # Google Maps puts each business in a card with structured text
        
        # Method 1: Query for all divs in the results area
        try:
            # The sidebar results are typically in a scrollable container
            # Each result is a card with business info
            
            # Get page content
            content = await page.content()
            
            # Parse business cards from the HTML
            # Google Maps uses specific patterns in the rendered HTML
            businesses = self._parse_from_html(content, max_results)
            
            if businesses and progress_callback:
                for biz in businesses:
                    progress_callback("business", biz)
                    progress_callback("count", len([b for b in businesses if b.company_name]))
            
            if not businesses:
                # Method 2: Try to find and click on result cards
                businesses = await self._extract_by_clicking(page, max_results, progress_callback)
                
        except Exception as e:
            if progress_callback:
                progress_callback("status", f"Extraction error: {str(e)[:50]}")
        
        return businesses
    
    def _parse_from_html(self, html: str, max_results: Optional[int]) -> List[Business]:
        """Parse business data from rendered HTML."""
        businesses = []
        
        # Look for business name patterns in the HTML
        # Google Maps renders businesses with specific structures
        
        # Pattern: Business names are often in aria-labels or specific divs
        name_patterns = [
            r'aria-label="([^"]{3,100})"[^>]*>([^<]*)',  # aria-label contains name
        ]
        
        # Find all text blocks that look like business listings
        # Each listing typically has: Name, Category, Address, Phone
        
        # Look for divs with business-like content
        # Google Maps uses data-attribute indexes for results
        result_pattern = r'data-result-index="(\d+)"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>'
        
        # Alternative: look for specific card structures
        # Try simpler approach - extract all reasonable text patterns
        
        # Find potential business names (capitalized words, 2-5 words)
        potential_names = re.findall(r'>([A-Z][A-Za-z0-9\s&\-\.,]+(?:LLC|Inc|Corp|Company|Co\.?|Ltd)?)<', html)
        
        # Find phone numbers
        phones = re.findall(r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4}', html)
        
        # Find addresses (number followed by street)
        addresses = re.findall(r'\d+\s+[A-Za-z0-9\s,.]+(?:St|Ave|Rd|Blvd|Dr|Ln|Way|Suite|Ste)', html, re.I)
        
        # Create businesses from found data
        for i, name in enumerate(potential_names[:50]):
            name = name.strip()
            if len(name) > 3 and len(name) < 100:
                biz = Business(company_name=name)
                
                if i < len(phones):
                    biz.phone = phones[i]
                if i < len(addresses):
                    biz.address = addresses[i]
                
                businesses.append(biz)
                
                if max_results and len(businesses) >= max_results:
                    break
        
        return businesses
    
    async def _extract_by_clicking(self, page, max_results, progress_callback) -> List[Business]:
        """Extract by clicking on result cards and getting details."""
        businesses = []
        seen = set()
        
        # Find all clickable result cards
        card_selectors = [
            '[data-result-index]',
            'a[href*="/maps/place/"]',
        ]
        
        for selector in card_selectors:
            try:
                cards = await page.query_selector_all(selector)
                
                for i, card in enumerate(cards[:20]):  # Process first 20
                    if max_results and len(businesses) >= max_results:
                        break
                    
                    try:
                        # Get text from card
                        text = await card.text_content()
                        if not text:
                            continue
                        
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        if not lines:
                            continue
                        
                        name = lines[0]
                        if len(name) < 2 or name.lower() in seen:
                            continue
                        
                        seen.add(name.lower())
                        
                        biz = Business(company_name=name)
                        
                        # Extract other info from lines
                        for line in lines[1:]:
                            # Phone
                            if re.search(r'\d{3}[-\s\.]?\d{3}[-\s\.]?\d{4}', line):
                                biz.phone = line
                            # Address
                            elif re.search(r'\d+.*(?:St|Ave|Rd|Blvd|Dr)', line, re.I):
                                biz.address = line
                            # Website (contains .com, .org, etc)
                            elif any(x in line.lower() for x in ['.com', '.org', '.net', 'www.']):
                                if not biz.website:
                                    biz.website = line if line.startswith('http') else f"https://{line}"
                            # Category (business type words)
                            elif any(x in line.lower() for x in ['electrician', 'contractor', 'service', 'repair', 'company']):
                                if not biz.category:
                                    biz.category = line
                        
                        businesses.append(biz)
                        
                        if progress_callback:
                            progress_callback("business", biz)
                            progress_callback("count", len(businesses))
                        
                    except Exception as e:
                        continue
                        
            except Exception as e:
                continue
        
        return businesses
