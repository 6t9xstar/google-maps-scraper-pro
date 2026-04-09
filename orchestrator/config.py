"""Configuration module for Google Maps Scraper."""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
PROXY_FILE = BASE_DIR / "proxies.txt"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(exist_ok=True)

# Scraping settings
DEFAULT_WORKERS = 50
MAX_WORKERS = 100
DEFAULT_TIMEOUT = 30
RETRY_ATTEMPTS = 3

# Google Maps settings
BASE_URL = "https://www.google.com/maps/search/"
RESULTS_PER_PAGE = 20

# CSV settings
CSV_ENCODING = "utf-8-sig"
CSV_COLUMNS = ["company_name", "website", "email", "category"]
