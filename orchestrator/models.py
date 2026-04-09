"""Data models for Google Maps scraper."""
from pydantic import BaseModel, Field
from typing import Optional


class Business(BaseModel):
    """Business data model."""
    company_name: str = Field(..., description="Company name")
    website: Optional[str] = Field(None, description="Business website URL")
    email: Optional[str] = Field(None, description="Contact email")
    category: Optional[str] = Field(None, description="Business category")
    
    class Config:
        populate_by_name = True


class SearchQuery(BaseModel):
    """Search query model."""
    query: str = Field(..., description="Search term")
    location: str = Field(..., description="Location")
    
    def to_url_format(self) -> str:
        """Convert to URL-friendly format."""
        search_term = f"{self.query} {self.location}"
        return search_term.replace(" ", "+")


class ScrapingConfig(BaseModel):
    """Scraping configuration."""
    workers: int = Field(default=50, ge=1, le=100)
    timeout: int = Field(default=30, ge=5)
    retry_attempts: int = Field(default=3, ge=1)
    use_proxies: bool = Field(default=False)
    max_results: Optional[int] = Field(default=None, description="Max results to scrape (None = unlimited)")
