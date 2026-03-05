"""
Web scraping discovery source for the multi-source discovery pipeline.

Uses Firecrawl to scrape product websites, documentation pages, and API docs.
Supports both targeted scraping of known URLs and fallback crawling of a base URL.
"""

import re
from typing import Optional, List
from datetime import datetime

from src.discovery.models import (
    SourceType,
    ConfidenceLevel,
    SourcedFact,
    SourceResult,
)


# Tech keywords matching processor.py patterns for consistent extraction
TECH_KEYWORDS = {
    "programming_languages": [
        "python", "javascript", "typescript", "java", "go", "rust",
        "ruby", "php", "c++", "c#", "swift", "kotlin",
    ],
    "frameworks": [
        "react", "vue", "angular", "django", "flask", "express",
        "spring", "laravel", "rails",
    ],
    "databases": [
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "cassandra", "dynamodb",
    ],
    "cloud": [
        "aws", "azure", "gcp", "google cloud", "amazon web services",
    ],
    "tools": [
        "docker", "kubernetes", "terraform", "ansible", "jenkins", "git",
    ],
    "apis": ["rest", "graphql", "grpc", "soap"],
    "protocols": ["http", "https", "websocket", "mqtt"],
}


class WebScrapingDiscovery:
    """
    Discovers product information by scraping websites using Firecrawl.

    Two modes of operation:
    - Targeted mode: scrapes specific URLs (docs, API pages) discovered by other sources
    - Fallback mode: crawls the main product URL to discover content
    """

    def __init__(self, firecrawl_client=None):
        """
        Initialize web scraping discovery.

        Args:
            firecrawl_client: Optional FirecrawlClient instance.
                If None, attempts to create one from config.
                If creation fails (no API key), methods return a failure result.
        """
        self.firecrawl = firecrawl_client
        self._firecrawl_available = firecrawl_client is not None

        if self.firecrawl is None:
            try:
                from src.ingestion import FirecrawlClient
                self.firecrawl = FirecrawlClient()
                self._firecrawl_available = True
            except Exception:
                self._firecrawl_available = False

    def discover(
        self,
        url: str,
        crawl_depth: int = 1,
        target_urls: Optional[List[str]] = None,
    ) -> SourceResult:
        """
        Discover product information by scraping web pages.

        Args:
            url: Base product URL to scrape or crawl from.
            crawl_depth: How deep to crawl when in fallback mode (default 1).
            target_urls: Optional list of specific URLs to scrape (docs, API pages).
                When provided, uses targeted mode instead of broad crawling.

        Returns:
            SourceResult with extracted capabilities, tech stack, and raw content.
        """
        if not self._firecrawl_available:
            return SourceResult(
                source_type=SourceType.WEB_SCRAPE,
                success=False,
                error="Firecrawl not available",
            )

        try:
            all_markdown_parts: List[str] = []
            scraped_urls: List[str] = []
            docs_urls: List[str] = []

            if target_urls:
                # Targeted mode: scrape each known URL individually
                all_markdown_parts, scraped_urls, docs_urls = self._scrape_targeted(
                    target_urls
                )
            else:
                # Fallback mode: scrape main URL + crawl linked pages
                all_markdown_parts, scraped_urls, docs_urls = self._scrape_fallback(
                    url, crawl_depth
                )

            # Combine all markdown into a single block of raw content
            raw_content = "\n\n---\n\n".join(all_markdown_parts)

            # Extract capabilities from headings
            capabilities = self._extract_capabilities(raw_content, scraped_urls, docs_urls)

            # Extract technology mentions
            tech_stack = self._extract_tech_mentions(raw_content)

            # Build discovered URLs for other pipeline stages
            discovered_urls = {}
            if url:
                discovered_urls["product_url"] = url

            return SourceResult(
                source_type=SourceType.WEB_SCRAPE,
                success=True,
                product_url=url,
                capabilities=capabilities,
                technical_stack=tech_stack,
                raw_content=raw_content[:50000] if raw_content else "",
                discovered_urls=discovered_urls,
            )

        except Exception as e:
            return SourceResult(
                source_type=SourceType.WEB_SCRAPE,
                success=False,
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scrape_targeted(
        self, target_urls: List[str]
    ) -> tuple:
        """Scrape each target URL individually (targeted mode)."""
        all_markdown: List[str] = []
        scraped_urls: List[str] = []
        docs_urls: List[str] = []

        for target_url in target_urls:
            try:
                result = self.firecrawl.scrape_url(
                    target_url,
                    options={
                        "formats": ["markdown", "html"],
                        "onlyMainContent": True,
                    },
                )
                markdown = result.get("markdown", "") if isinstance(result, dict) else str(result)
                if markdown:
                    all_markdown.append(markdown)
                    scraped_urls.append(target_url)
                    # Docs / API pages get MEDIUM confidence later
                    docs_urls.append(target_url)
            except Exception as exc:
                print(f"Warning: Failed to scrape target URL {target_url}: {exc}")

        return all_markdown, scraped_urls, docs_urls

    def _scrape_fallback(
        self, url: str, crawl_depth: int
    ) -> tuple:
        """Scrape main URL and crawl linked pages (fallback mode)."""
        all_markdown: List[str] = []
        scraped_urls: List[str] = []
        docs_urls: List[str] = []

        # 1. Scrape the main URL
        try:
            main_result = self.firecrawl.scrape_url(
                url,
                options={
                    "formats": ["markdown", "html"],
                    "onlyMainContent": True,
                },
            )
            main_md = (
                main_result.get("markdown", "")
                if isinstance(main_result, dict)
                else str(main_result)
            )
            if main_md:
                all_markdown.append(main_md)
                scraped_urls.append(url)
        except Exception as exc:
            print(f"Warning: Failed to scrape main URL {url}: {exc}")

        # 2. Crawl linked pages
        try:
            crawl_results = self.firecrawl.crawl_website(
                url, max_depth=crawl_depth, limit=15
            )
            for page in crawl_results:
                page_md = (
                    page.get("markdown", "")
                    if isinstance(page, dict)
                    else str(page)
                )
                page_url = (
                    page.get("url", "")
                    if isinstance(page, dict)
                    else getattr(page, "url", "")
                )
                if page_md:
                    all_markdown.append(page_md)
                    scraped_urls.append(page_url)
                    # Identify docs pages by URL pattern
                    if self._is_docs_page(page_url):
                        docs_urls.append(page_url)
        except Exception as exc:
            print(f"Warning: Crawl failed for {url}: {exc}")

        return all_markdown, scraped_urls, docs_urls

    @staticmethod
    def _is_docs_page(url: str) -> bool:
        """Heuristic: determine if a URL is a documentation or API page."""
        if not url:
            return False
        url_lower = url.lower()
        docs_indicators = [
            "/docs", "/documentation", "/api", "/reference",
            "/guide", "/tutorial", "/manual", "/sdk",
            "/developer", "/getting-started",
        ]
        return any(indicator in url_lower for indicator in docs_indicators)

    def _extract_capabilities(
        self,
        raw_content: str,
        scraped_urls: List[str],
        docs_urls: List[str],
    ) -> List[SourcedFact]:
        """
        Extract capabilities from markdown headings.

        Headings from docs pages get MEDIUM confidence; landing pages get LOW.
        """
        capabilities: List[SourcedFact] = []
        seen_values: set = set()

        for line in raw_content.splitlines():
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue

            # Strip markdown heading markers and formatting
            heading_text = re.sub(r"^#+\s*", "", stripped)
            heading_text = re.sub(r"\*\*|__|\*|_|`", "", heading_text)
            heading_text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", heading_text)
            heading_text = heading_text.strip()

            if not heading_text or len(heading_text) < 3:
                continue

            normalized = heading_text.lower()
            if normalized in seen_values:
                continue
            seen_values.add(normalized)

            # Determine confidence: docs pages => MEDIUM, landing pages => LOW
            is_docs = any(self._is_docs_page(u) for u in docs_urls)
            confidence = ConfidenceLevel.MEDIUM if is_docs else ConfidenceLevel.LOW

            # Use the first scraped URL as source_url, or None
            source_url = scraped_urls[0] if scraped_urls else None

            capabilities.append(
                SourcedFact(
                    value=heading_text,
                    source=SourceType.WEB_SCRAPE,
                    source_url=source_url,
                    confidence=confidence,
                    raw_evidence=stripped[:200],
                )
            )

        return capabilities

    @staticmethod
    def _extract_tech_mentions(raw_content: str) -> List[SourcedFact]:
        """
        Extract technology mentions from content using regex keyword matching.

        Uses the same keyword categories as processor.py for consistency.
        """
        tech_facts: List[SourcedFact] = []
        content_lower = raw_content.lower()
        seen: set = set()

        for _category, keywords in TECH_KEYWORDS.items():
            for keyword in keywords:
                if keyword in seen:
                    continue
                # Use word-boundary search for short keywords to avoid false matches
                if len(keyword) <= 3:
                    pattern = rf"\b{re.escape(keyword)}\b"
                    if re.search(pattern, content_lower):
                        seen.add(keyword)
                        tech_facts.append(
                            SourcedFact(
                                value=keyword,
                                source=SourceType.WEB_SCRAPE,
                                confidence=ConfidenceLevel.LOW,
                            )
                        )
                elif keyword in content_lower:
                    seen.add(keyword)
                    tech_facts.append(
                        SourcedFact(
                            value=keyword,
                            source=SourceType.WEB_SCRAPE,
                            confidence=ConfidenceLevel.LOW,
                        )
                    )

        return tech_facts
