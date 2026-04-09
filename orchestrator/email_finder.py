"""Email extraction module for finding emails on websites."""
import re
import httpx
from typing import Optional, Set
from urllib.parse import urljoin, urlparse
import asyncio
from bs4 import BeautifulSoup


class EmailFinder:
    """Finds email addresses on websites."""
    
    EMAIL_REGEX = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.found_emails: Set[str] = set()
    
    async def extract_from_website(self, url: str) -> Optional[str]:
        """Extract email from a website. Returns first valid email found."""
        if not url or not url.startswith(('http://', 'https://')):
            return None
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                # Try homepage first
                response = await client.get(url)
                if response.status_code == 200:
                    emails = self._extract_emails(response.text)
                    if emails:
                        return emails[0]
                
                # Try common pages where email might be found
                pages_to_try = ['contact', 'about', 'contact-us', 'about-us']
                parsed = urlparse(url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                
                for page in pages_to_try:
                    try:
                        page_url = urljoin(base_url, page)
                        response = await client.get(page_url)
                        if response.status_code == 200:
                            emails = self._extract_emails(response.text)
                            if emails:
                                return emails[0]
                    except:
                        continue
                
                return None
                
        except Exception:
            return None
    
    def _extract_emails(self, html: str) -> list:
        """Extract emails from HTML content."""
        # Remove common obfuscation patterns
        cleaned = html.replace(' at ', '@').replace(' [at] ', '@').replace('[at]', '@')
        cleaned = cleaned.replace(' dot ', '.').replace(' [dot] ', '.').replace('[dot]', '.')
        
        # Find all emails
        emails = self.EMAIL_REGEX.findall(cleaned)
        
        # Filter valid emails
        valid_emails = []
        for email in emails:
            email = email.lower().strip()
            # Skip common false positives
            if any(x in email for x in ['example.', 'test.', 'noreply', 'no-reply', 'support@', 'info@']):
                continue
            if email not in self.found_emails:
                valid_emails.append(email)
                self.found_emails.add(email)
        
        return valid_emails
