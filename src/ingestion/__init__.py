"""
Data ingestion module for Step 1.
Handles scraping and fetching of technical documentation, code, and API specs.
"""

from .firecrawl_client import FirecrawlClient

__all__ = ["FirecrawlClient"]
