"""CSV writer module for exporting scraped data."""
import csv
from pathlib import Path
from typing import List
from models import Business
from config import CSV_ENCODING, CSV_COLUMNS, OUTPUT_DIR


class CSVWriter:
    """Handles CSV file operations."""
    
    def __init__(self, filename: str):
        self.filepath = OUTPUT_DIR / filename
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create CSV file with headers if it doesn't exist."""
        if not self.filepath.exists():
            with open(self.filepath, 'w', newline='', encoding=CSV_ENCODING) as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
    
    def write_business(self, business: Business):
        """Write a single business to CSV."""
        with open(self.filepath, 'a', newline='', encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writerow(business.model_dump())
    
    def write_businesses(self, businesses: List[Business]):
        """Write multiple businesses to CSV."""
        with open(self.filepath, 'a', newline='', encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            for business in businesses:
                writer.writerow(business.model_dump())
    
    def get_stats(self) -> dict:
        """Get CSV file statistics."""
        if not self.filepath.exists():
            return {"rows": 0, "size": 0}
        
        with open(self.filepath, 'r', encoding=CSV_ENCODING) as f:
            row_count = sum(1 for _ in f) - 1  # Exclude header
        
        return {
            "rows": max(0, row_count),
            "size": self.filepath.stat().st_size
        }
