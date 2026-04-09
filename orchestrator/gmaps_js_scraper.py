"""Google Maps scraper using in-browser JavaScript evaluation."""
import asyncio
import re
from typing import List, Optional
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
from models import Business


class GMapsJSScraper:
    """Scrapes Google Maps using JavaScript execution in browser."""
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxy_list = proxy_list or []
        
    async def scrape(
        self, 
        query: str, 
        location: str, 
        max_results: Optional[int] = None,
        progress_callback = None
    ) -> List[Business]:
        """Scrape Google Maps using JS injection."""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            try:
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                
                page = await context.new_page()
                
                # Build URL
                url = f"https://www.google.com/maps/search/{quote_plus(query)}+{quote_plus(location)}"
                
                if progress_callback:
                    progress_callback("status", f"Loading Google Maps...")
                
                # Navigate with shorter timeout
                await page.goto(url, timeout=30000)
                
                # Wait for any content to load
                await asyncio.sleep(5)
                
                if progress_callback:
                    progress_callback("status", f"Searching for results...")
                
                # Method: Extract all text from search result cards using JS
                businesses = await self._extract_via_js(page, max_results, progress_callback)
                
                await context.close()
                return businesses
                
            finally:
                await browser.close()
    
    async def _extract_via_js(self, page, max_results, progress_callback) -> List[Business]:
        """Extract using JavaScript evaluation."""
        businesses = []
        
        # JavaScript to extract business data from the page
        js_code = """
        () => {
            const results = [];
            
            // Try multiple selectors for business listings
            const selectors = [
                '[role="feed"] > div > div',
                '[data-result-index]',
                '.m6QErb > div',
                'a[href*="/maps/place/"]',
                '[role="article"]'
            ];
            
            let elements = [];
            for (const sel of selectors) {
                const found = document.querySelectorAll(sel);
                if (found.length > 0) {
                    elements = Array.from(found);
                    break;
                }
            }
            
            for (const el of elements) {
                const text = el.innerText || el.textContent;
                if (text) {
                    const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
                    if (lines.length > 0) {
                        // Try to find business name (usually first line or a link)
                        let name = lines[0];
                        
                        // Look for phone
                        let phone = '';
                        let address = '';
                        let website = '';
                        let category = '';
                        
                        for (const line of lines) {
                            // Phone pattern
                            if (/\\d{3}[-\\s.]?\\d{3}[-\\s.]?\\d{4}/.test(line)) {
                                phone = line;
                            }
                            // Address pattern (starts with number)
                            else if (/^\\d+\\s+/.test(line) && (line.includes('St') || line.includes('Ave') || line.includes('Rd') || line.includes('Blvd'))) {
                                address = line;
                            }
                            // Website
                            else if (line.includes('.com') || line.includes('.org') || line.includes('www.')) {
                                website = line;
                            }
                            // Category indicators
                            else if (/electrician|contractor|service|repair|company|inc\.?|llc/i.test(line)) {
                                category = line;
                            }
                        }
                        
                        results.push({
                            name: name,
                            phone: phone,
                            address: address,
                            website: website,
                            category: category,
                            raw: lines.slice(0, 5).join(' | ')
                        });
                    }
                }
            }
            
            return results;
        }
        """
        
        try:
            raw_results = await page.evaluate(js_code)
            
            if progress_callback:
                progress_callback("status", f"Found {len(raw_results)} raw entries")
            
            seen = set()
            for data in raw_results[:50]:
                name = data.get('name', '').strip()
                
                # Skip duplicates and invalid names
                if not name or len(name) < 2:
                    continue
                    
                key = name.lower()
                if key in seen or key in ['', 'google', 'maps', 'search']:
                    continue
                seen.add(key)
                
                # Filter out non-business names
                if any(x in name.lower() for x in ['review', 'rating', 'star', 'photos', 'directions']):
                    continue
                
                biz = Business(company_name=name)
                
                if data.get('phone'):
                    biz.phone = data['phone']
                if data.get('address'):
                    biz.address = data['address']
                if data.get('website'):
                    biz.website = data['website']
                if data.get('category'):
                    biz.category = data['category']
                
                businesses.append(biz)
                
                if progress_callback:
                    progress_callback("business", biz)
                    progress_callback("count", len(businesses))
                
                if max_results and len(businesses) >= max_results:
                    break
                    
        except Exception as e:
            if progress_callback:
                progress_callback("status", f"JS extraction error: {str(e)[:50]}")
        
        return businesses
