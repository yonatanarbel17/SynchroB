# Step 1: Product Analysis

Step 1 analyzes product pages and extracts comprehensive functional information including capabilities, pricing, tech stack, integrations, and API endpoints.

## Features

- ✅ **Web Scraping**: Uses Firecrawl to extract content from main page
- ✅ **Linked Page Crawling**: Automatically crawls docs, API, pricing, and integration pages
- ✅ **GPT-4 Analysis**: Uses ChatGPT/GPT-4 for high-quality analysis (default)
- ✅ **Comprehensive Extraction**: Extracts pricing, tech stack, integrations, API endpoints, and functionality
- ✅ **Markdown Output**: Generates beautiful markdown reports (default)
- ✅ **JSON Output**: Also supports JSON format for programmatic use

## Usage

### Command Line

```bash
# Basic usage (analyze a product page with GPT-4, markdown output)
python step1_cli.py https://example.com/product

# Save to specific file
python step1_cli.py https://example.com/product -o my_analysis.md

# Output as JSON instead of markdown
python step1_cli.py https://example.com/product -f json

# Use Gemini instead of GPT-4 (cost-effective)
python step1_cli.py https://example.com/product --use-gemini

# Crawl linked pages with custom depth (default: 2)
python step1_cli.py https://example.com/product --crawl-depth 3
```

### Python API

```python
from src.step1 import Step1Processor

# Initialize processor (uses Gemini by default)
processor = Step1Processor(use_gemini=True)

# Analyze a product
result = processor.analyze_product("https://example.com/product")

# Access results
print(result['analysis']['summary'])
print(result['analysis']['capabilities'])
print(result['extracted_data']['title'])

# Save to file
processor.save_output(result, "output.json")
```

## Output Structure

### Markdown Format (Default)

The markdown report includes:
- Product summary
- Capabilities list
- Use cases
- Technical stack
- Integrations
- API endpoints
- Pricing information
- Extracted data (headings, links, etc.)

### JSON Format

The JSON structure includes:

```json
{
  "url": "https://example.com/product",
  "timestamp": "2024-01-01T12:00:00",
  "main_page": {
    "markdown": "...",
    "html": "...",
    "metadata": {...}
  },
  "linked_pages": [
    {
      "url": "https://example.com/docs",
      "markdown": "...",
      "metadata": {...}
    }
  ],
  "extracted_data": {
    "title": "Product Name",
    "description": "...",
    "headings": [...],
    "links": [...],
    "code_blocks": [...],
    "features": [...],
    "api_endpoints_raw": [...],
    "pricing_mentions": [...],
    "tech_stack_mentions": [...]
  },
  "analysis": {
    "summary": "What the product does",
    "capabilities": ["capability1", "capability2"],
    "use_cases": ["use case 1", "use case 2"],
    "technical_stack": ["tech1", "tech2"],
    "integrations": ["integration1", "integration2"],
    "api_endpoints": ["/api/v1/endpoint1", "/api/v1/endpoint2"],
    "pricing": {
      "model": "subscription",
      "tiers": ["Free", "Pro: $10/month", "Enterprise: Custom"],
      "free_tier": true,
      "notes": "14-day free trial"
    },
    "target_audience": "Who uses it",
    "category": "Product category",
    "deployment": "SaaS"
  }
}
```

## What Gets Extracted

- **Functionality**: What the product does, capabilities, use cases
- **Pricing**: Pricing model, tiers, free tier availability
- **Technical Stack**: Technologies, frameworks, languages used
- **Integrations**: Third-party services, APIs, plugins
- **API Endpoints**: API documentation and endpoints
- **Deployment**: Cloud, on-premise, SaaS, etc.
- **Target Audience**: Who the product is for
- **Category**: Product classification

## Examples

```bash
# Analyze a SaaS product (Stripe)
python step1_cli.py https://stripe.com

# Analyze with custom crawl depth
python step1_cli.py https://stripe.com --crawl-depth 3

# Get JSON output for programmatic use
python step1_cli.py https://stripe.com -f json -o stripe_analysis.json

# Use Gemini for cost-effective analysis
python step1_cli.py https://stripe.com --use-gemini
```
