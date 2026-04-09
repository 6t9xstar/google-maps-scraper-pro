"""Google Maps scraper using Playwright for JavaScript rendering."""
import asyncio
import json
import re
from typing import List, Optional
from playwright.async_api import async_playwright, Page
from models import Business


class GoogleMapsScraper:
    """Scrapes Google Maps using Playwright browser automation."""
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxy_list = proxy_list or []
        self.proxy_index = 0
        self.results: List[Business] = []
        self.seen_names = set()
        
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
        """Scrape Google Maps for businesses."""
        search_term = f"{query} {location}"
        
        async with async_playwright() as p:
            # Try without proxy first, then with proxies if available
            proxy_attempts = [None]  # No proxy first
            if self.proxy_list:
                proxy_attempts.extend(self.proxy_list[:3])  # Try up to 3 proxies
            
            browser = None
            last_error = None
            
            for proxy in proxy_attempts:
                try:
                    browser_config = {"headless": True}
                    if proxy:
                        browser_config["proxy"] = {"server": proxy}
                        if progress_callback:
                            progress_callback("status", f"Trying proxy: {proxy[:30]}...")
                    else:
                        if progress_callback:
                            progress_callback("status", "Connecting without proxy...")
                    
                    browser = await p.chromium.launch(**browser_config)
                    break  # Success, exit loop
                    
                except Exception as e:
                    last_error = e
                    if proxy:
                        if progress_callback:
                            progress_callback("status", f"Proxy failed: {str(e)[:50]}")
                    continue
            
            if not browser:
                raise Exception(f"Failed to launch browser: {last_error}")
            
            try:
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                page = await context.new_page()
                
                # Navigate to Google Maps search
                encoded_search = search_term.replace(" ", "+")
                url = f"https://www.google.com/maps/search/{encoded_search}"
                
                if progress_callback:
                    progress_callback("status", f"Navigating to Google Maps...")
                
                await page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Wait for results to load
                await asyncio.sleep(3)
                
                # Extract business data
                businesses = await self._extract_businesses(page, max_results, progress_callback)
                
                await context.close()
                
                return businesses
                
            finally:
                await browser.close()
    
    async def _extract_businesses(
        self, 
        page: Page, 
        max_results: Optional[int],
        progress_callback
    ) -> List[Business]:
        """Extract business listings from the page."""
        businesses = []
        
        # Try multiple selectors for business cards
        selectors = [
            '[data-result-index]',
            '[jsaction*="mouseover"]',
            '.bfdHYe',
            '.V0h1Ob',
            '[role="article"]',
            '.qBF1Pd',
            'a[href*="/maps/place/"]'
        ]
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    if progress_callback:
                        progress_callback("status", f"Found {len(elements)} listings with {selector}")
                    break
            except:
                continue
        else:
            elements = []
        
        if not elements:
            # Try to get any links that look like place links
            elements = await page.query_selector_all('a[href*="/maps/place/"]')
        
        # Limit results if specified
        if max_results:
            elements = elements[:max_results]
        
        for i, element in enumerate(elements):
            try:
                business = await self._extract_business_data(page, element)
                if business and business.company_name:
                    # Avoid duplicates
                    if business.company_name not in self.seen_names:
                        self.seen_names.add(business.company_name)
                        businesses.append(business)
                        
                        if progress_callback:
                            progress_callback("business", business)
                            progress_callback("count", len(businesses))
            except Exception as e:
                continue
        
        return businesses
    
    async def _extract_business_data(self, page: Page, element) -> Optional[Business]:
        """Extract data from a single business element."""
        business = Business()
        
        # Try multiple approaches to get the name
        name_selectors = [
            'h3',
            '.qBF1Pd',
            '.fontHeadlineSmall',
            '[role="heading"]',
            'span[title]'
        ]
        
        for selector in name_selectors:
            try:
                name_elem = await element.query_selector(selector)
                if name_elem:
                    name = await name_elem.text_content()
                    if name:
                        business.company_name = name.strip()
                        break
            except:
                continue
        
        if not business.company_name:
            # Try getting text content directly
            try:
                text = await element.text_content()
                if text:
                    # First line is usually the name
                    lines = text.strip().split('\n')
                    if lines:
                        business.company_name = lines[0].strip()
            except:
                pass
        
        # Extract website
        try:
            # Look for website link
            website_selectors = [
                'a[href^="http"]',
                'a[data-item-id="website"]'
            ]
            
            for selector in website_selectors:
                link = await element.query_selector(selector)
                if link:
                    href = await link.get_attribute('href')
                    if href and not href.startswith('/maps'):
                        business.website = href
                        break
        except:
            pass
        
        # Extract category
        try:
            category_selectors = [
                '.W4Efsd span',
                '.fontBodyMedium span',
                '.gwmHr'
            ]
            
            for selector in category_selectors:
                cat_elem = await element.query_selector(selector)
                if cat_elem:
                    category = await cat_elem.text_content()
                    if category:
                        business.category = category.strip()
                        break
        except:
            pass
        
        return business if business.company_name else None
