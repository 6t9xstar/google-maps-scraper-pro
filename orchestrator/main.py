#!/usr/bin/env python3
"""Main orchestrator for Google Maps Scraper."""
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from tqdm import tqdm

from config import PROXY_FILE, DEFAULT_WORKERS, OUTPUT_DIR
from csv_writer import CSVWriter
from email_finder import EmailFinder
from models import Business, SearchQuery, ScrapingConfig
from proxy_scraper import ProxyScraper


class ScraperOrchestrator:
    """Orchestrates the scraping process."""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.email_finder = EmailFinder()
        self.proxy_list = self._load_proxies()
        
    def _load_proxies(self) -> list:
        """Load proxies from file."""
        if not self.config.use_proxies or not PROXY_FILE.exists():
            return []
        
        with open(PROXY_FILE, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        click.echo(f"Loaded {len(proxies)} proxies")
        return proxies
    
    async def run_scraper(self, query: SearchQuery, output_file: str):
        """Run the Go scraper and process results."""
        csv_writer = CSVWriter(output_file)
        
        # Build Go scraper command
        agents_dir = Path(__file__).parent.parent / "agents"
        go_scraper = agents_dir / "scraper.exe" if sys.platform == "win32" else agents_dir / "scraper"
        
        if not go_scraper.exists():
            click.echo("Building Go scraper...")
            self._build_go_scraper(agents_dir)
        
        # Prepare config for Go scraper
        scraper_config = {
            "query": query.query,
            "location": query.location,
            "workers": self.config.workers,
            "timeout": self.config.timeout,
            "retry_attempts": self.config.retry_attempts,
            "proxies": self.proxy_list,
            "max_results": self.config.max_results
        }
        
        # Run Go scraper
        click.echo(f"Starting scrape: {query.query} in {query.location}")
        click.echo(f"Workers: {self.config.workers}")
        
        process = await asyncio.create_subprocess_exec(
            str(go_scraper),
            json.dumps(scraper_config),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Process results in real-time
        processed = 0
        with tqdm(desc="Processing results", unit=" businesses") as pbar:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                try:
                    data = json.loads(line.decode().strip())
                    
                    if data.get("type") == "business":
                        business = Business(**data["data"])
                        
                        # Extract email if website exists
                        if business.website and not business.email:
                            business.email = await self.email_finder.extract_from_website(business.website)
                        
                        csv_writer.write_business(business)
                        processed += 1
                        pbar.update(1)
                        
                    elif data.get("type") == "progress":
                        pbar.set_postfix({"page": data.get("page", 0)})
                        
                    elif data.get("type") == "error":
                        tqdm.write(f"Error: {data.get('message', 'Unknown error')}")
                        
                except json.JSONDecodeError:
                    continue
        
        await process.wait()
        
        # Show final stats
        stats = csv_writer.get_stats()
        click.echo(f"\n✓ Scraping complete!")
        click.echo(f"  Total businesses: {stats['rows']}")
        click.echo(f"  Output file: {csv_writer.filepath}")
    
    def _build_go_scraper(self, agents_dir: Path):
        """Build the Go scraper binary."""
        result = subprocess.run(
            ["go", "build", "-o", "scraper", "."],
            cwd=agents_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            click.echo(f"Failed to build Go scraper: {result.stderr}")
            sys.exit(1)


async def fetch_fresh_proxies():
    """Fetch fresh proxies from public sources."""
    click.echo("Fetching fresh proxies from public sources...")
    scraper = ProxyScraper()
    proxies = await scraper.fetch_all_proxies()
    
    if proxies:
        count = scraper.save_to_file(str(PROXY_FILE))
        click.echo(f"✓ Saved {count} fresh proxies to proxies.txt")
        return True
    else:
        click.echo("✗ Failed to fetch proxies")
        return False


@click.command()
@click.option('--query', '-q', prompt='Search query', help='What to search for (e.g., restaurants)')
@click.option('--location', '-l', prompt='Location', help='Location to search in (e.g., New York)')
@click.option('--output', '-o', default='results.csv', help='Output CSV filename')
@click.option('--workers', '-w', default=DEFAULT_WORKERS, help='Number of concurrent workers')
@click.option('--max-results', '-m', default=None, type=int, help='Maximum results to scrape (default: unlimited)')
@click.option('--use-proxies', is_flag=True, help='Use proxies from proxies.txt')
@click.option('--fetch-proxies', is_flag=True, help='Fetch fresh proxies before scraping')
def main(query: str, location: str, output: str, workers: int, max_results: Optional[int], use_proxies: bool, fetch_proxies: bool):
    """Google Maps Unlimited Scraper - Professional Desktop Tool"""
    click.echo("╔════════════════════════════════════════════════╗")
    click.echo("║     Google Maps Unlimited Scraper v1.0        ║")
    click.echo("║         Professional Desktop Edition           ║")
    click.echo("╚════════════════════════════════════════════════╝\n")
    
    # Fetch fresh proxies if requested
    if fetch_proxies:
        success = asyncio.run(fetch_fresh_proxies())
        if not success and not use_proxies:
            click.echo("Warning: No proxies available, continuing without proxies")
        use_proxies = success or use_proxies
    
    # Create config
    config = ScrapingConfig(
        workers=workers,
        use_proxies=use_proxies,
        max_results=max_results
    )
    
    # Create search query
    search_query = SearchQuery(query=query, location=location)
    
    # Run scraper
    orchestrator = ScraperOrchestrator(config)
    asyncio.run(orchestrator.run_scraper(search_query, output))


if __name__ == "__main__":
    main()
