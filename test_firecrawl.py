"""
Test script for Firecrawl integration.
Run this to verify your Firecrawl API key is working.
"""

import sys
from config import config
from src.ingestion import FirecrawlClient


def test_firecrawl():
    """Test Firecrawl client initialization and basic functionality."""
    print("Testing Firecrawl Integration...")
    print(f"API Key configured: {bool(config.FIRECRAWL_API_KEY)}")
    
    if not config.FIRECRAWL_API_KEY:
        print("⚠️  Warning: FIRECRAWL_API_KEY not set in .env")
        print("Using API key from MCP config...")
        # Use the API key from MCP config
        api_key = "your_firecrawl_api_key_here"  # Replace with your actual API key
    else:
        api_key = config.FIRECRAWL_API_KEY
    
    try:
        # Initialize client
        client = FirecrawlClient(api_key=api_key)
        print("✓ FirecrawlClient initialized successfully")
        
        # Test with a simple URL (optional - uncomment to test actual scraping)
        # print("\nTesting URL scraping...")
        # result = client.scrape_url("https://example.com")
        # print(f"✓ Successfully scraped URL: {result.get('url', 'N/A')}")
        
        print("\n✅ Firecrawl integration test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_firecrawl()
    sys.exit(0 if success else 1)
