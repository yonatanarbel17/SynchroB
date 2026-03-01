# Ingestion Module

This module handles data ingestion for Step 1 of SynchroB.

## FirecrawlClient

The `FirecrawlClient` class provides methods for:
- Scraping individual URLs
- Batch scraping multiple URLs
- Crawling entire websites
- Extracting technical documentation
- Fetching API specifications

## Usage

```python
from src.ingestion import FirecrawlClient
from config import config

# Initialize client (uses API key from config)
client = FirecrawlClient()

# Scrape a single URL
result = client.scrape_url("https://example.com/docs")

# Extract technical docs from multiple URLs
urls = [
    "https://api.example.com/docs",
    "https://github.com/user/repo/blob/main/README.md"
]
docs = client.extract_technical_docs(urls)

# Get API specifications
api_spec = client.get_api_specs("https://api.example.com/openapi.json")
```

## MCP Integration

The Firecrawl MCP server is configured separately. The API key from your MCP config (`fc-b4714ee8a2124d93b0ba3449b627d795`) can be used with this client by setting it in your `.env` file or passing it directly:

```python
client = FirecrawlClient(api_key="fc-b4714ee8a2124d93b0ba3449b627d795")
```
