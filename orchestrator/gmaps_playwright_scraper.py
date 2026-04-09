"""Google Maps scraper using Playwright - extracts rich data like working tools."""
import asyncio
import re
from typing import List, Optional
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
from models import Business


class GMapsPlaywrightScraper:
    """Scrapes Google Maps using Playwright browser automation."""
    
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
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            try:
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                page = await context.new_page()
                
                # Use Google Maps search URL with ?q= parameter (like working tools)
                url = f"https://www.google.com/maps?q={quote_plus(search_term)}"
                
                if progress_callback:
                    progress_callback("status", f"Loading Google Maps...")
                
                await page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Wait for results panel to appear
                try:
                    await page.wait_for_selector('[role="feed"], [data-result-index], .m6QErb, .bfdHYe', timeout=10000)
                except:
                    if progress_callback:
                        progress_callback("status", "No results panel found, waiting more...")
                    await asyncio.sleep(5)
                
                if progress_callback:
                    progress_callback("status", "Page loaded, extracting data...")
                
                # Extract businesses
                businesses = await self._extract_businesses(page, max_results, progress_callback)
                
                if progress_callback:
                    progress_callback("status", f"Extracted {len(businesses)} businesses")
                
                await context.close()
                return businesses
                
            finally:
                await browser.close()
    
    async def _extract_businesses(
        self, 
        page, 
        max_results: Optional[int],
        progress_callback
    ) -> List[Business]:
        """Extract business listings from Google Maps."""
        businesses = []
        seen = set()
        
        # Try to find the results feed/scrollable area
        feed_selectors = [
            '[role="feed"] > div',  # Main results feed
            '[data-result-index]',  # Individual result cards
            '.m6QErb .bfdHYe',      # Alternative card selector
            '[role="article"]',     # Article cards
            'a[href*="/maps/place/"]',  # Place links
        ]
        
        found_selector = None
        for selector in feed_selectors:
            try:
                count = await page.eval_on_selector_all(selector, 'elements => elements.length')
                if progress_callback:
                    progress_callback("status", f"Selector '{selector}': {count} elements")
                if count > 0:
                    found_selector = selector
                    break
            except Exception as e:
                if progress_callback:
                    progress_callback("status", f"Selector '{selector}' failed: {str(e)[:50]}")
        
        if not found_selector:
            if progress_callback:
                progress_callback("status", "No results found on page")
            return []
        
        # Get all elements with the working selector
        try:
            elements = await page.query_selector_all(found_selector)
            if progress_callback:
                progress_callback("status", f"Found {len(elements)} potential listings")
        except Exception as e:
            if progress_callback:
                progress_callback("status", f"Failed to get elements: {str(e)[:50]}")
            return []
        
        for elem in elements[:50]:  # Process up to 50
            if max_results and len(businesses) >= max_results:
                break
            
            try:
                business = await self._extract_listing_data(elem, page)
                if business and business.company_name:
                    key = business.company_name.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        businesses.append(business)
                        
                        if progress_callback:
                            progress_callback("business", business)
                            progress_callback("count", len(businesses))
            except Exception as e:
                if progress_callback:
                    progress_callback("status", f"Extraction error: {str(e)[:30]}")
        
        return businesses
    
    async def _extract_listing_data(self, elem, page) -> Optional[Business]:
        """Extract data from a single listing element."""
        business = Business()
        
        # Get all text content from the element
        try:
            text = await elem.text_content()
            if not text:
                return None
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if not lines:
                return None
            
            # First non-empty line is usually the business name
            business.company_name = lines[0]
            
            # Look for category in the next few lines
            for line in lines[1:4]:
                if any(x in line.lower() for x in [
                    'restaurant', 'doctor', 'contractor', 'electrician', 'service', 
                    'store', 'shop', 'clinic', 'hospital', 'plumber', 'lawyer',
                    'dentist', 'repair', 'company', 'inc', 'llc', 'corp'
                ]):
                    business.category = line[:100]
                    break
            
            # Look for phone in all lines
            for line in lines:
                phone_match = re.search(r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4}', line)
                if phone_match:
                    business.phone = phone_match.group(0)
                    break
            
            # Look for address (contains numbers and street-like words)
            for line in lines:
                if re.search(r'\d+.*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Suite|Ste|#\d+)', line, re.I):
                    business.address = line[:200]
                    break
            
            # Get website from links
            try:
                href = await elem.get_attribute('href')
                if href and '/maps/place/' in href:
                    # This is a place link, extract place ID or get more details
                    pass
            except:
                pass
            
            # Look for external website links within the element
            try:
                links = await elem.query_selector_all('a')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and href.startswith('http') and 'google.com' not in href:
                        business.website = href
                        break
            except:
                pass
            
        except Exception as e:
            return None
        
        return business if business.company_name else None
