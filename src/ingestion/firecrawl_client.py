"""
Firecrawl client for web scraping and content extraction.
Supports both direct API usage and MCP integration.
"""

from typing import Optional, Dict, List, Any
from firecrawl import FirecrawlApp
from src.utils import setup_logger
from config import config

logger = setup_logger(__name__)


class FirecrawlClient:
    """
    Client for Firecrawl API and MCP integration.
    
    This client handles:
    - Scraping technical documentation
    - Extracting content from landing pages
    - Fetching API documentation
    - Processing GitHub README files
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Firecrawl client.
        
        Args:
            api_key: Firecrawl API key. If None, uses config.FIRECRAWL_API_KEY
        """
        self.api_key = api_key or config.FIRECRAWL_API_KEY
        if not self.api_key:
            raise ValueError(
                "Firecrawl API key is required. "
                "Set FIRECRAWL_API_KEY in .env or pass it to FirecrawlClient."
            )
        self.app = FirecrawlApp(api_key=self.api_key)
    
    def scrape_url(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Scrape a single URL and extract content.
        
        Args:
            url: URL to scrape
            options: Optional scraping options (formats, onlyMainContent, etc.)
        
        Returns:
            Dictionary containing scraped content and metadata
        """
        # Default options
        formats = ["markdown", "html"]
        only_main_content = True
        
        # Override with provided options
        if options:
            formats = options.get("formats", formats)
            only_main_content = options.get("onlyMainContent", options.get("only_main_content", only_main_content))
        
        try:
            result = self.app.scrape(
                url,
                formats=formats,
                only_main_content=only_main_content
            )
            # Convert result to dict format
            if hasattr(result, 'markdown'):
                # Handle Document object
                metadata = {}
                if hasattr(result, 'metadata'):
                    meta_obj = result.metadata
                    if hasattr(meta_obj, '__dict__'):
                        metadata = meta_obj.__dict__
                    elif isinstance(meta_obj, dict):
                        metadata = meta_obj
                    else:
                        # Try to get common metadata fields
                        metadata = {
                            "title": getattr(meta_obj, 'title', ''),
                            "description": getattr(meta_obj, 'description', ''),
                        }
                
                return {
                    "markdown": result.markdown,
                    "html": getattr(result, 'html', ''),
                    "metadata": metadata,
                    "url": url,
                }
            elif isinstance(result, dict):
                return result
            else:
                # Fallback: convert to dict
                return {
                    "markdown": str(result),
                    "html": "",
                    "metadata": {},
                    "url": url,
                }
        except Exception as e:
            raise Exception(f"Error scraping {url}: {str(e)}")
    
    def scrape_urls(self, urls: List[str], options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs in batch.
        
        Args:
            urls: List of URLs to scrape
            options: Optional scraping options
        
        Returns:
            List of dictionaries containing scraped content for each URL
        """
        results = []
        for url in urls:
            try:
                result = self.scrape_url(url, options)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {str(e)}")
                results.append({"url": url, "error": str(e)})
        return results
    
    def crawl_website(self, url: str, max_depth: int = 2, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Crawl a website starting from a base URL.
        
        Args:
            url: Base URL to start crawling from
            max_depth: Maximum depth to crawl
            limit: Maximum number of pages to crawl
        
        Returns:
            List of scraped pages
        """
        try:
            # Use start_crawl for async crawling
            crawl_result = self.app.start_crawl(
                url,
                max_depth=max_depth,
                limit=limit,
                formats=["markdown", "html"],
                only_main_content=True
            )
            
            # Get crawl ID
            crawl_id = None
            if isinstance(crawl_result, dict):
                crawl_id = crawl_result.get("crawlId")
            elif hasattr(crawl_result, 'crawlId'):
                crawl_id = crawl_result.crawlId
            
            if crawl_id:
                # Poll for status and get results
                import time
                max_wait = 60  # Wait up to 60 seconds
                waited = 0
                while waited < max_wait:
                    status = self.app.get_crawl_status(crawl_id)
                    status_dict = status if isinstance(status, dict) else status.__dict__ if hasattr(status, '__dict__') else {}
                    
                    if status_dict.get("status") == "completed":
                        # Get the results
                        pages = self.app.get_crawl_status_page(crawl_id, page=1)
                        results = []
                        pages_data = pages if isinstance(pages, dict) else pages.__dict__ if hasattr(pages, '__dict__') else {}
                        
                        if "data" in pages_data:
                            for page in pages_data["data"]:
                                page_dict = page if isinstance(page, dict) else page.__dict__ if hasattr(page, '__dict__') else {}
                                results.append({
                                    "url": page_dict.get("url", ""),
                                    "markdown": page_dict.get("markdown", ""),
                                    "metadata": page_dict.get("metadata", {})
                                })
                        return results
                    elif status_dict.get("status") == "failed":
                        raise Exception(f"Crawl failed: {status_dict.get('error', 'Unknown error')}")
                    time.sleep(2)
                    waited += 2
                
                # Timeout - return partial results if available
                try:
                    pages = self.app.get_crawl_status_page(crawl_id, page=1)
                    pages_data = pages if isinstance(pages, dict) else pages.__dict__ if hasattr(pages, '__dict__') else {}
                    if "data" in pages_data:
                        return [{"url": p.get("url", "") if isinstance(p, dict) else getattr(p, "url", ""), 
                                "markdown": p.get("markdown", "") if isinstance(p, dict) else getattr(p, "markdown", ""), 
                                "metadata": p.get("metadata", {}) if isinstance(p, dict) else getattr(p, "metadata", {})} 
                               for p in pages_data["data"]]
                except Exception:
                    pass
            
            return []
        except Exception as e:
            # If start_crawl fails, return empty list (crawling is optional)
            logger.warning(f"Could not crawl linked pages: {str(e)}")
            return []
    
    def extract_technical_docs(self, urls: List[str]) -> Dict[str, Any]:
        """
        Extract technical documentation from a list of URLs.
        Optimized for API docs, READMEs, and technical content.
        
        Args:
            urls: List of URLs containing technical documentation
        
        Returns:
            Dictionary with extracted content organized by URL
        """
        results = {}
        for url in urls:
            try:
                content = self.scrape_url(url, options={
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                })
                results[url] = {
                    "content": content.get("markdown", ""),
                    "html": content.get("html", ""),
                    "metadata": content.get("metadata", {}),
                    "success": True,
                }
            except Exception as e:
                results[url] = {
                    "error": str(e),
                    "success": False,
                }
        return results
    
    def get_api_specs(self, api_doc_url: str) -> Dict[str, Any]:
        """
        Extract API specification from documentation URL.
        
        Args:
            api_doc_url: URL to API documentation (OpenAPI, GraphQL, etc.)
        
        Returns:
            Dictionary containing API spec content
        """
        try:
            content = self.scrape_url(api_doc_url, options={
                "formats": ["markdown", "html"],
                "onlyMainContent": True,
            })
            return {
                "url": api_doc_url,
                "markdown": content.get("markdown", ""),
                "html": content.get("html", ""),
                "metadata": content.get("metadata", {}),
            }
        except Exception as e:
            raise Exception(f"Error extracting API specs from {api_doc_url}: {str(e)}")
