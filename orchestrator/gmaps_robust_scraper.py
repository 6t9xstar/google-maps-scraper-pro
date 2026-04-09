"""Robust Google Maps scraper using Playwright with proper waiting and scrolling."""
import asyncio
import re
from typing import List, Optional
from urllib.parse import quote_plus
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from models import Business


class GMapsRobustScraper:
    """Robust scraper that properly waits for and extracts Google Maps data."""
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxy_list = proxy_list or []
        
    async def scrape(
        self, 
        query: str, 
        location: str, 
        max_results: Optional[int] = None,
        progress_callback = None
    ) -> List[Business]:
        """Scrape Google Maps with proper loading and scrolling."""
        
        search_term = f"{query} {location}"
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            try:
                # Create context with realistic viewport
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="en-US",
                )
                
                page = await context.new_page()
                
                # Build URL
                url = f"https://www.google.com/maps/search/{quote_plus(query)}+{quote_plus(location)}"
                
                if progress_callback:
                    progress_callback("status", f"Navigating to Google Maps...")
                
                # Navigate with longer timeout
                await page.goto(url, wait_until="load", timeout=60000)
                
                # Wait for page to settle
                await asyncio.sleep(3)
                
                if progress_callback:
                    progress_callback("status", f"Waiting for results to load...")
                
                # Try to find and wait for results container
                results_found = await self._wait_for_results(page, progress_callback)
                
                if not results_found:
                    if progress_callback:
                        progress_callback("status", "No results container found, trying alternative...")
                    await asyncio.sleep(5)
                
                # Extract data using JavaScript
                businesses = await self._extract_data_js(page, max_results, progress_callback)
                
                await context.close()
                return businesses
                
            finally:
                await browser.close()
    
    async def _wait_for_results(self, page, progress_callback) -> bool:
        """Wait for results to appear on the page."""
        selectors = [
            '[role="feed"]',
            '[data-result-index]',
            '.m6QErb',
            'a[href*="/maps/place/"]',
        ]
        
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=10000)
                if progress_callback:
                    progress_callback("status", f"Results loaded (selector: {selector})")
                return True
            except:
                continue
        
        return False
    
    async def _extract_data_js(self, page, max_results, progress_callback) -> List[Business]:
        """Extract business data using JavaScript evaluation."""
        businesses = []
        seen = set()
        
        # JavaScript to find and extract all business listings
        extract_js = r"""
        () => {
            const results = [];
            
            // Function to extract data from a card
            function extractFromCard(card) {
                const data = {
                    name: '',
                    category: '',
                    address: '',
                    phone: '',
                    website: ''
                };
                
                // Try different selectors for name
                const nameSelectors = [
                    'h3',
                    '.fontHeadlineSmall',
                    '.qBF1Pd',
                    '[role="heading"]',
                    'div[class*="title"]',
                    'div[class*="name"]'
                ];
                
                for (const sel of nameSelectors) {
                    const el = card.querySelector(sel);
                    if (el && el.textContent.trim()) {
                        data.name = el.textContent.trim();
                        break;
                    }
                }
                
                // If no name found, try first text content
                if (!data.name) {
                    const allText = card.innerText || card.textContent;
                    if (allText) {
                        const lines = allText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
                        if (lines.length > 0) {
                            data.name = lines[0];
                        }
                    }
                }
                
                // Get all text lines for parsing
                const text = card.innerText || card.textContent || '';
                const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
                
                for (const line of lines) {
                    // Phone pattern
                    if (/\d{3}[-\s.]*\d{3}[-\s.]*\d{4}/.test(line) && line.length < 20) {
                        data.phone = line;
                    }
                    // Address pattern
                    else if(/^\d+\s+/.test(line) && (line.includes('St') || line.includes('Ave') || line.includes('Rd') || line.includes('Blvd'))) {
                        data.address = line;
                    }
                    // Website
                    else if ((line.includes('.com') || line.includes('.org') || line.includes('www.')) && !line.includes('google.')) {
                        data.website = line;
                    }
                    // Category (common business types)
                    else if (/restaurant|doctor|contractor|electrician|service|repair|company|inc\.?|llc|shop|store|clinic/i.test(line)) {
                        if (!data.category && line.length < 50) {
                            data.category = line;
                        }
                    }
                }
                
                // Look for website in links
                const links = card.querySelectorAll('a');
                for (const link of links) {
                    const href = link.getAttribute('href');
                    if (href && href.startsWith('http') && !href.includes('google.com')) {
                        data.website = href;
                        break;
                    }
                }
                
                return data;
            }
            
            // Try to find all business cards
            const cardSelectors = [
                '[role="feed"] > div > div',
                '[data-result-index]',
                '.m6QErb > div > div',
                '[role="article"]',
                'a[href*="/maps/place/"]'
            ];
            
            let cards = [];
            for (const sel of cardSelectors) {
                cards = document.querySelectorAll(sel);
                if (cards.length > 0) {
                    break;
                }
            }
            
            for (const card of cards) {
                const data = extractFromCard(card);
                if (data.name && data.name.length > 1) {
                    results.push(data);
                }
            }
            
            return results;
        }
        """
        
        try:
            # Get initial results
            raw_results = await page.evaluate(extract_js)
            if raw_results is None:
                raw_results = []
            
            if progress_callback:
                progress_callback("status", f"Found {len(raw_results)} initial results")
            
            # Process results
            for data in raw_results:
                name = data.get('name', '').strip()
                
                # Clean and validate name
                if not name or len(name) < 2:
                    continue
                
                # Skip duplicates
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                
                # Filter out non-business text
                skip_words = ['review', 'rating', 'star', 'photos', 'directions', 'save', 'share', 'call', 'website', 'results']
                if any(word in key for word in skip_words):
                    continue
                
                biz = Business(company_name=name)
                
                if data.get('category'):
                    biz.category = data['category']
                if data.get('address'):
                    biz.address = data['address']
                if data.get('phone'):
                    biz.phone = data['phone']
                if data.get('website'):
                    biz.website = data['website']
                
                businesses.append(biz)
                
                if progress_callback:
                    progress_callback("business", biz)
                    progress_callback("count", len(businesses))
                
                if max_results and len(businesses) >= max_results:
                    break
            
            # Try scrolling for more results if needed
            if not max_results or len(businesses) < max_results:
                await self._scroll_and_extract(page, businesses, seen, max_results, progress_callback)
                
        except Exception as e:
            if progress_callback:
                progress_callback("status", f"Extraction error: {str(e)[:50]}")

    async def _scroll_and_extract(self, page, businesses, seen, max_results, progress_callback):
        """Scroll and extract more results."""
        scroll_attempts = 0
        max_scrolls = 15
        no_new_count = 0
        
        while scroll_attempts < max_scrolls and no_new_count < 3:
            if max_results and len(businesses) >= max_results:
                break
            
            # Scroll down in the results panel
            await page.evaluate("""
                () => {
                    const feed = document.querySelector('[role="feed"]');
                    if (feed) {
                        feed.scrollTop = feed.scrollHeight;
                    } else {
                        window.scrollBy(0, 800);
                    }
                }
            """)
            await asyncio.sleep(3)
            
            # Extract again
            extract_js = r"""
            () => {
                const results = [];
                const cards = document.querySelectorAll('[role="feed"] > div > div, [data-result-index]');
                
                for (const card of cards) {
                    const text = card.innerText || card.textContent || '';
                    const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
                    
                    if (lines.length > 0) {
                        results.push({
                            name: lines[0],
                            raw: lines.slice(0, 3).join(' | ')
                        });
                    }
                }
                
                return results;
            }
            """
            
            try:
                new_results = await page.evaluate(extract_js)
                if new_results is None:
                    new_results = []
                added_count = 0
                
                for data in new_results:
                    name = data.get('name', '').strip()
                    
                    if not name or len(name) < 2:
                        continue
                    
                    key = name.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    
                    skip_words = ['review', 'rating', 'star', 'photos', 'directions', 'results']
                    if any(word in key for word in skip_words):
                        continue
                    
                    biz = Business(company_name=name)
                    businesses.append(biz)
                    added_count += 1
                    
                    if progress_callback:
                        progress_callback("business", biz)
                        progress_callback("count", len(businesses))
                    
                    if max_results and len(businesses) >= max_results:
                        break
                
                # Track if we found new results
                if added_count == 0:
                    no_new_count += 1
                    if progress_callback:
                        progress_callback("status", f"No new results after scroll ({no_new_count}/3)")
                else:
                    no_new_count = 0
                    if progress_callback:
                        progress_callback("status", f"Added {added_count} new businesses (total: {len(businesses)})")
                
                if len(new_results) == 0:
                    break
                    
            except Exception as e:
                if progress_callback:
                    progress_callback("status", f"Scroll extract error: {str(e)[:30]}")
                break
            
            scroll_attempts += 1
