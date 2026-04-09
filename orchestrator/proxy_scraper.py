"""Proxy scraper module for fetching free proxies from public sources."""
import asyncio
from typing import List, Set
import httpx


class ProxyScraper:
    """Fetches free proxies from public sources."""
    
    SOURCES = {
        "http": [
            "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/http.txt",
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=1000&country=all&ssl=all&anonymity=all",
        ],
        "socks4": [
            "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks4.txt",
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=1000&country=all",
        ],
        "socks5": [
            "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks5.txt",
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=1000&country=all",
        ]
    }
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.proxies: Set[str] = set()
    
    async def fetch_all_proxies(self) -> List[str]:
        """Fetch proxies from all sources."""
        tasks = []
        
        for protocol, urls in self.SOURCES.items():
            for url in urls:
                tasks.append(self._fetch_from_url(url, protocol))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                self.proxies.update(result)
        
        return list(self.proxies)
    
    async def _fetch_from_url(self, url: str, protocol: str) -> List[str]:
        """Fetch proxies from a single URL."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                content = response.text
                return self._parse_proxies(content, protocol)
        except Exception:
            return []
    
    def _parse_proxies(self, content: str, protocol: str) -> List[str]:
        """Parse proxy list from content."""
        proxies = []
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Check if already has protocol prefix
            if line.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
                proxies.append(line)
            else:
                # Add protocol prefix
                if protocol == "http":
                    proxies.append(f"http://{line}")
                elif protocol == "socks4":
                    proxies.append(f"socks4://{line}")
                elif protocol == "socks5":
                    proxies.append(f"socks5://{line}")
        
        return proxies
    
    def save_to_file(self, filepath: str) -> int:
        """Save proxies to file. Returns count of saved proxies."""
        with open(filepath, 'w') as f:
            for proxy in sorted(self.proxies):
                f.write(f"{proxy}\n")
        return len(self.proxies)
    
    async def get_working_proxies(self, max_check: int = 100) -> List[str]:
        """Test proxies and return working ones (optional validation)."""
        test_url = "http://httpbin.org/ip"
        working = []
        
        # Test a sample of proxies
        sample = list(self.proxies)[:max_check]
        
        async def test_proxy(proxy: str) -> bool:
            try:
                async with httpx.AsyncClient(
                    proxy=proxy,
                    timeout=10
                ) as client:
                    response = await client.get(test_url)
                    return response.status_code == 200
            except:
                return False
        
        # Test concurrently
        tasks = [test_proxy(p) for p in sample]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for proxy, is_working in zip(sample, results):
            if is_working is True:
                working.append(proxy)
        
        return working
