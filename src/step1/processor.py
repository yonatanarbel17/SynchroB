"""
Step 1 Processor: Analyzes product pages and extracts functional information.

Supports two entry modes:
  - analyze_product(url)          → single-source (Firecrawl scraping only)
  - analyze_product_by_name(name) → multi-source discovery pipeline
"""

from typing import Dict, Any, Optional, List
import json
import re
from datetime import datetime

from src.ingestion import FirecrawlClient
from src.analysis import GeminiClient, OpenAIClient, ClaudeClient
from src.step1.analysis_strategy import (
    AnalysisStrategy,
    DirectAnalysisStrategy,
    GeminiAnalysisStrategy,
    OpenAIAnalysisStrategy,
    ClaudeAnalysisStrategy,
)
from src.discovery.orchestrator import DiscoveryOrchestrator
from src.discovery.merger import SourceMerger
from src.discovery.models import (
    MergedDiscoveryResult,
    SourceType,
    ConfidenceLevel,
)
from src.utils import setup_logger
from config import config

logger = setup_logger(__name__)


class Step1Processor:
    """
    Step 1: Product Analysis Processor
    
    Takes a product URL and outputs:
    - All important data from the page
    - Summary of what the product does
    - Product capabilities
    """
    
    def __init__(self, analysis_strategy: Optional[AnalysisStrategy] = None,
                 use_gemini: bool = False, use_llm: bool = False):
        """
        Initialize Step 1 processor.

        Args:
            analysis_strategy: Optional custom analysis strategy. If None, will be auto-selected.
            use_gemini: If True, prefer Gemini when use_llm=True. Default: False
            use_llm: If True, use LLM APIs for analysis. Default: False (direct analysis).

        When use_llm=True, the priority order is:
          1. Claude (Anthropic) — the default / go-to
          2. Gemini (if use_gemini=True or Claude unavailable)
          3. OpenAI (fallback)
          4. Direct analysis (final fallback)
        """
        self.firecrawl = FirecrawlClient()

        # Initialize analysis strategy
        if analysis_strategy is not None:
            self.analysis_strategy = analysis_strategy
        elif use_llm:
            self.analysis_strategy = self._init_llm_strategy(use_gemini)
        else:
            self.analysis_strategy = DirectAnalysisStrategy(self._generate_intelligent_analysis)

        logger.info(f"Using analysis strategy: {self.analysis_strategy.get_name()}")

    def _init_llm_strategy(self, use_gemini: bool) -> AnalysisStrategy:
        """Try Claude first, then Gemini/OpenAI, then direct analysis."""
        fallback = self._generate_intelligent_analysis

        # 1. Try Claude first (default / go-to)
        if config.ANTHROPIC_API_KEY:
            try:
                claude_client = ClaudeClient()
                return ClaudeAnalysisStrategy(fallback, claude_client)
            except Exception as e:
                logger.warning(f"Could not initialize Claude client: {e}")

        # 2. Try Gemini
        if use_gemini or config.GEMINI_API_KEY:
            try:
                gemini_client = GeminiClient()
                return GeminiAnalysisStrategy(fallback, gemini_client)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini client: {e}")

        # 3. Try OpenAI
        if config.OPENAI_API_KEY:
            try:
                openai_client = OpenAIClient()
                return OpenAIAnalysisStrategy(fallback, openai_client)
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")

        # 4. Final fallback
        logger.info("No LLM client available, using direct intelligent analysis")
        return DirectAnalysisStrategy(fallback)
    
    def analyze_product(self, url: str, crawl_depth: int = 2) -> Dict[str, Any]:
        """
        Analyze a product from its main page URL.
        
        Args:
            url: Product main page URL
            crawl_depth: Depth to crawl linked pages (docs, API, etc.). Default: 2
        
        Returns:
            Dictionary containing all extracted data and analysis
        """
        logger.info(f"Analyzing product: {url}")

        # Step 1: Scrape the main page
        logger.info("Scraping main page...")
        main_page_data = self._scrape_page(url)
        
        # Step 2: Crawl linked pages (docs, API, etc.)
        linked_pages_data = []
        if crawl_depth > 0:
            logger.info(f"Crawling linked pages (depth: {crawl_depth})...")
            linked_pages_data = self._crawl_linked_pages(url, crawl_depth)
        
        # Step 3: Combine all scraped content
        all_content = self._combine_content(main_page_data, linked_pages_data)
        
        # Step 4: Extract important data
        logger.info("Extracting important data...")
        extracted_data = self._extract_important_data(all_content)
        
        # Step 5: Generate comprehensive analysis using selected strategy
        logger.info(f"Generating analysis using {self.analysis_strategy.get_name()}...")
        analysis = self.analysis_strategy.analyze(all_content, extracted_data, url)
        
        # Step 6: Combine all data
        result = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "main_page": main_page_data,
            "linked_pages": linked_pages_data,
            "extracted_data": extracted_data,
            "analysis": analysis,
        }
        
        logger.info("Analysis complete!")
        return result

    # ------------------------------------------------------------------
    # Multi-source discovery entry point
    # ------------------------------------------------------------------

    def analyze_product_by_name(
        self,
        product_name: str,
        product_url: Optional[str] = None,
        crawl_depth: int = 1,
        skip_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze a product using multi-source discovery.

        Instead of relying solely on web scraping, this method queries:
          1. LLM knowledge base (baseline) — skipped in cursor/skip_llm mode
          2. Package registries (PyPI, NPM)
          3. OpenAPI/Swagger spec probing
          4. GitHub repository analysis
          5. Targeted web scraping (docs pages discovered by other sources)

        The output dict is a backward-compatible superset of analyze_product().
        Step 2 (generalizer) can consume it without changes.

        Args:
            product_name: Product name (e.g. "stripe", "twilio", "etoro")
            product_url:  Optional product URL. If None, will be auto-discovered.
            crawl_depth:  Depth for web scraping phase (default: 1)
            skip_llm:     If True, skip all external LLM API calls (cursor mode).
                          Discovery still runs non-LLM sources and the analysis
                          is built directly from discovery data. Cursor's own LLM
                          can then analyze the structured output.

        Returns:
            Dictionary with same schema as analyze_product() PLUS
            discovery_metadata and enriched analysis fields.
        """
        logger.info(f"Analyzing product by name: {product_name}")
        logger.info("=" * 60)

        # 1. Build discovery orchestrator with available clients
        gemini_client = None if skip_llm else self._get_llm_client("gemini")
        openai_client = None if skip_llm else self._get_llm_client("openai")

        # Firecrawl may not be configured — that's OK in multi-source mode
        firecrawl_client = None
        try:
            firecrawl_client = self.firecrawl
        except Exception:
            pass

        orchestrator = DiscoveryOrchestrator(
            gemini_client=gemini_client,
            openai_client=openai_client,
            firecrawl_client=firecrawl_client,
            github_token=getattr(config, "GITHUB_TOKEN", None),
        )

        # 2. Run multi-source discovery
        if skip_llm:
            logger.info("Running discovery (no external LLM calls)...")
        else:
            logger.info("Running multi-source discovery...")
        source_results = orchestrator.run_discovery(
            product_name,
            product_url=product_url,
            crawl_depth=crawl_depth,
        )

        # 3. Merge all source results
        logger.info("Merging discovery results...")
        merger = SourceMerger()
        merged = merger.merge(source_results, product_name)

        # 4. Convert merged data into the format the analysis strategy expects
        all_content = self._merged_to_scraped_format(merged)
        extracted_data = self._extract_important_data(all_content)

        # 5. Enrich extracted_data with discovery-specific data
        extracted_data = self._enrich_with_discovery(extracted_data, merged)

        effective_url = product_url or merged.product_url or product_name

        # 6. Generate analysis
        if skip_llm:
            # Cursor mode: build analysis directly from discovery data
            # (no external LLM calls — Cursor's own LLM analyzes the output)
            logger.info("Building analysis from discovery data (cursor mode)...")
            analysis = self._build_discovery_analysis(merged, extracted_data, effective_url)
        else:
            # Normal mode: run analysis strategy on enriched data
            logger.info(f"Generating analysis using {self.analysis_strategy.get_name()}...")
            analysis = self.analysis_strategy.analyze(all_content, extracted_data, effective_url)

        # 7. Augment analysis with discovery data that strategies don't know about
        analysis = self._augment_analysis(analysis, merged)

        # 8. Build result (backward-compatible with analyze_product output)
        result = {
            "product_name": product_name,
            "url": effective_url,
            "timestamp": datetime.now().isoformat(),
            "main_page": {
                "markdown": merged.combined_content[:10000],
                "html": "",
                "metadata": {
                    "title": product_name,
                    "description": merged.description or "",
                },
                "url": effective_url,
            },
            "linked_pages": [],
            "extracted_data": extracted_data,
            "analysis": analysis,
            "discovery_metadata": {
                "sources_used": [s.value for s in merged.sources_used],
                "sources_failed": merged.sources_failed,
                "overall_confidence": merged.overall_confidence.value,
                "source_coverage": merged.source_coverage,
                "mode": "cursor" if skip_llm else "full",
                "needs_cursor_analysis": skip_llm,
            },
        }

        logger.info("Multi-source analysis complete!")
        sc = merged.source_coverage
        success_count = sum(1 for v in sc.values() if v)
        logger.info(f"Sources: {success_count}/{len(sc)} succeeded")
        logger.info(f"Confidence: {merged.overall_confidence.value}")
        logger.info(f"Capabilities: {len(analysis.get('capabilities', []))}")
        logger.info(f"API endpoints: {len(analysis.get('api_endpoints', []))}")
        logger.info(f"SDK languages: {len(analysis.get('sdk_languages', []))}")
        if skip_llm:
            logger.info("Cursor mode: output is ready for Cursor's LLM to analyze")

        return result

    # ------------------------------------------------------------------
    # Multi-source helper methods
    # ------------------------------------------------------------------

    def _build_discovery_analysis(
        self,
        merged: MergedDiscoveryResult,
        extracted_data: Dict[str, Any],
        effective_url: str,
    ) -> Dict[str, Any]:
        """
        Build an analysis dict directly from merged discovery data.

        This is used in cursor mode (skip_llm=True) to produce a clean,
        structured analysis without calling any external LLM API.
        Cursor's own LLM can then interpret and enrich this output.
        """
        # Capabilities: use discovery facts, sorted by confidence
        capabilities = [f.value for f in merged.capabilities]

        # API endpoints
        api_endpoints = []
        for ep in merged.api_endpoints:
            ep_str = f"{ep.method} {ep.path}" if ep.method else ep.path
            api_endpoints.append(ep_str)

        # Technical stack
        technical_stack = list(dict.fromkeys(
            f.value for f in merged.technical_stack
            if f.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
        ))

        # Integrations
        integrations = list(dict.fromkeys(
            f.value for f in merged.integrations
        ))

        # SDK languages
        sdk_languages = list(dict.fromkeys(
            f.value for f in merged.sdk_languages
        ))

        # Auth methods
        auth_methods = list(dict.fromkeys(
            f.value for f in merged.auth_methods
        ))

        # Architecture
        architecture = [f.value for f in merged.architecture_patterns] if merged.architecture_patterns else []
        deployment = [f.value for f in merged.deployment_options] if merged.deployment_options else []

        # Description / summary
        summary = merged.description or extracted_data.get("description", "")
        if not summary:
            summary = f"Technical analysis of {merged.product_name}"

        # Build the analysis dict (same schema as strategy output)
        analysis = {
            "summary": summary,
            "capabilities": capabilities,
            "use_cases": [],  # Left empty — Cursor's LLM should generate these
            "technical_stack": technical_stack,
            "integrations": integrations,
            "api_endpoints": api_endpoints,
            "sdk_languages": sdk_languages,
            "auth_methods": auth_methods,
            "architecture_patterns": architecture,
            "deployment_options": deployment,
            "pricing": {
                "model": "unknown",
                "tiers": [],
                "free_tier": "unknown",
                "notes": "Pricing requires LLM analysis or manual review."
            },
            "target_audience": "",  # Left empty — Cursor's LLM should infer
            "category": "",  # Left empty — Cursor's LLM should classify
            "deployment": deployment[0] if deployment else "Unknown",
            "cursor_mode": True,
            "note": (
                "This analysis was built from discovery data without external LLM calls. "
                "Use Cursor's AI to analyze the raw data in 'extracted_data' and "
                "'discovery_metadata' for deeper insights, category classification, "
                "use case generation, and target audience identification."
            ),
            # Raw provenance data for Cursor to analyze
            "raw_capabilities_with_sources": [f.to_dict() for f in merged.capabilities],
            "raw_endpoints_with_sources": [ep.to_dict() for ep in merged.api_endpoints],
        }

        return analysis

    def _get_llm_client(self, kind: str):
        """Try to get an LLM client, first from the strategy, then by creating one."""
        if kind == "gemini":
            if hasattr(self.analysis_strategy, "llm"):
                llm = self.analysis_strategy.llm
                if isinstance(llm, GeminiClient):
                    return llm
            try:
                return GeminiClient()
            except Exception:
                return None
        elif kind == "openai":
            if hasattr(self.analysis_strategy, "llm"):
                llm = self.analysis_strategy.llm
                if isinstance(llm, OpenAIClient):
                    return llm
            try:
                return OpenAIClient()
            except Exception:
                return None
        return None

    def _merged_to_scraped_format(self, merged: MergedDiscoveryResult) -> Dict[str, Any]:
        """
        Convert MergedDiscoveryResult into the dict format expected by
        _extract_important_data() and analysis strategies.
        """
        return {
            "markdown": merged.combined_content,
            "main_page": {
                "markdown": merged.combined_content[:5000],
                "html": "",
                "metadata": {
                    "title": merged.product_name,
                    "description": merged.description or "",
                },
                "url": merged.product_url or "",
            },
            "linked_pages": [],
            "total_pages": 1,
        }

    def _enrich_with_discovery(
        self, extracted_data: Dict[str, Any], merged: MergedDiscoveryResult
    ) -> Dict[str, Any]:
        """Add discovery-sourced data to extracted_data dict."""

        # SDK languages (new field)
        extracted_data["sdk_languages"] = [f.to_dict() for f in merged.sdk_languages]

        # Auth methods (new field)
        extracted_data["auth_methods"] = [f.to_dict() for f in merged.auth_methods]

        # Discovered dependencies (new field)
        extracted_data["discovered_dependencies"] = [
            f.to_dict() for f in merged.dependencies
        ]

        # Enrich existing API endpoints with discovery data
        discovery_endpoints = []
        for ep in merged.api_endpoints:
            ep_str = f"{ep.method} {ep.path}" if ep.method else ep.path
            if ep_str not in extracted_data.get("api_endpoints_raw", []):
                discovery_endpoints.append(ep_str)
        existing_raw = extracted_data.get("api_endpoints_raw", [])
        extracted_data["api_endpoints_raw"] = existing_raw + discovery_endpoints

        # Enrich tech stack with validated discovery data
        discovery_tech = set()
        for fact in merged.technical_stack:
            if fact.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
                discovery_tech.add(fact.value.lower())
        existing_tech = set(extracted_data.get("tech_stack_mentions", []))
        extracted_data["tech_stack_mentions"] = list(existing_tech | discovery_tech)

        # Add discovery description if extracted one is empty
        if not extracted_data.get("description") and merged.description:
            extracted_data["description"] = merged.description

        return extracted_data

    def _augment_analysis(
        self, analysis: Dict[str, Any], merged: MergedDiscoveryResult
    ) -> Dict[str, Any]:
        """Post-process analysis to inject discovery-sourced data."""

        # Inject full OpenAPI spec if found
        if merged.openapi_spec:
            analysis["api_spec"] = merged.openapi_spec

        # Add SDK languages
        analysis["sdk_languages"] = list(
            dict.fromkeys(f.value for f in merged.sdk_languages)
        )

        # Add auth methods
        analysis["auth_methods"] = list(
            dict.fromkeys(f.value for f in merged.auth_methods)
        )

        # Merge discovery capabilities into analysis capabilities
        existing_caps = set(
            c.lower().strip() for c in analysis.get("capabilities", [])
        )
        discovery_caps = []
        for fact in merged.capabilities:
            if fact.value.lower().strip() not in existing_caps:
                discovery_caps.append(fact.value)
                existing_caps.add(fact.value.lower().strip())
        analysis["capabilities"] = (
            analysis.get("capabilities", []) + discovery_caps
        )

        # Merge discovery endpoints into analysis endpoints
        existing_eps = set(str(e) for e in analysis.get("api_endpoints", []))
        for ep in merged.api_endpoints:
            ep_str = f"{ep.method} {ep.path}" if ep.method else ep.path
            if ep_str not in existing_eps:
                analysis.setdefault("api_endpoints", []).append(ep_str)
                existing_eps.add(ep_str)

        # Merge discovery integrations
        existing_integ = set(
            i.lower() for i in analysis.get("integrations", [])
        )
        for fact in merged.integrations:
            if fact.value.lower() not in existing_integ:
                analysis.setdefault("integrations", []).append(fact.value)
                existing_integ.add(fact.value.lower())

        # Add source tracking to evidence
        source_tracking = {}
        for field_name, facts in [
            ("capabilities", merged.capabilities),
            ("technical_stack", merged.technical_stack),
            ("integrations", merged.integrations),
        ]:
            source_tracking[field_name] = [
                {
                    "value": f.value,
                    "sources": [f.source.value],
                    "confidence": f.confidence.value,
                }
                for f in facts
            ]
        source_tracking["api_endpoints"] = [
            {
                "path": ep.path,
                "method": ep.method,
                "sources": [ep.source.value],
                "confidence": ep.confidence.value,
            }
            for ep in merged.api_endpoints
        ]
        analysis["source_tracking"] = source_tracking

        # Enrich evidence tracking
        evidence = analysis.get("evidence_tracking", {})
        facts = evidence.get("technical_facts", [])
        for src_type in merged.sources_used:
            facts.append(
                {
                    "fact": f"Data collected from {src_type.value}",
                    "evidence": f"Discovery source: {src_type.value}",
                    "confidence": "High"
                    if src_type
                    in (SourceType.OPENAPI_SPEC, SourceType.PACKAGE_REGISTRY)
                    else "Medium",
                }
            )
        evidence["technical_facts"] = facts

        # Adjust confidence level based on discovery coverage
        if merged.overall_confidence == ConfidenceLevel.HIGH:
            evidence["confidence_level"] = "High"
        elif merged.overall_confidence == ConfidenceLevel.MEDIUM:
            evidence["confidence_level"] = "Medium"
        analysis["evidence_tracking"] = evidence

        return analysis

    def _scrape_page(self, url: str) -> Dict[str, Any]:
        """Scrape a single page using Firecrawl."""
        try:
            result = self.firecrawl.scrape_url(url, options={
                "formats": ["markdown", "html"],
                "onlyMainContent": True,
            })
            return {
                "markdown": result.get("markdown", ""),
                "html": result.get("html", ""),
                "metadata": result.get("metadata", {}),
                "url": result.get("url", url),
            }
        except Exception as e:
            raise Exception(f"Error scraping {url}: {str(e)}")
    
    def _crawl_linked_pages(self, base_url: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Crawl linked pages (docs, API, etc.) with priority scoring for 'Technical Gold'."""
        try:
            # Crawl website
            pages = self.firecrawl.crawl_website(
                base_url,
                max_depth=max_depth,
                limit=30  # Get more pages to allow for priority filtering
            )
            
            # Score and prioritize pages (Technical Gold first)
            scored_pages = []
            for page in pages:
                url = page.get("url", "").lower()
                score = self._calculate_page_priority(url)
                
                scored_pages.append({
                    "url": page.get("url", ""),
                    "markdown": page.get("markdown", ""),
                    "metadata": page.get("metadata", {}),
                    "priority_score": score
                })
            
            # Sort by priority (highest first), then limit
            scored_pages.sort(key=lambda x: x["priority_score"], reverse=True)
            
            # Return top 15 prioritized pages
            relevant_pages = [
                {k: v for k, v in page.items() if k != "priority_score"}
                for page in scored_pages[:15]
            ]
            
            if relevant_pages:
                logger.info(f"Prioritized {len(relevant_pages)} technical pages (top priority: {scored_pages[0]['priority_score']})")
            
            return relevant_pages
            
        except Exception as e:
            logger.warning(f"Error crawling linked pages: {str(e)}")
            return []
    
    def _calculate_page_priority(self, url: str) -> int:
        """
        Calculate priority score for a page URL.
        Higher scores = more technical/valuable content.
        
        Technical Gold indicators:
        - swagger, openapi, graphql, npm, api-docs, spec
        - docs, documentation, developer, sdk
        - integrations, pricing (business logic)
        - blog, about (low priority)
        """
        url_lower = url.lower()
        score = 0
        
        # Technical Gold (highest priority) - API specs, schemas, technical docs
        technical_gold_keywords = {
            "swagger": 100,
            "openapi": 100,
            "graphql": 100,
            "npm": 90,
            "api-docs": 90,
            "api/docs": 90,
            "spec": 85,
            "schema": 85,
            "openapi.json": 100,
            "swagger.json": 100,
            "graphql.json": 100,
        }
        for keyword, points in technical_gold_keywords.items():
            if keyword in url_lower:
                score += points
        
        # High priority - Developer documentation
        high_priority_keywords = {
            "docs": 70,
            "documentation": 70,
            "developer": 65,
            "developers": 65,
            "sdk": 75,
            "api": 60,
            "reference": 60,
        }
        for keyword, points in high_priority_keywords.items():
            if keyword in url_lower:
                score += points
        
        # Medium priority - Business logic
        medium_priority_keywords = {
            "integrations": 50,
            "pricing": 45,
            "features": 40,
            "getting-started": 55,
            "quickstart": 55,
        }
        for keyword, points in medium_priority_keywords.items():
            if keyword in url_lower:
                score += points
        
        # Low priority (penalty) - Marketing content
        low_priority_keywords = {
            "blog": -20,
            "about": -15,
            "news": -10,
            "press": -10,
        }
        for keyword, penalty in low_priority_keywords.items():
            if keyword in url_lower:
                score += penalty
        
        # Base score for any page
        if score == 0:
            score = 10
        
        return score
    
    def _combine_content(self, main_page: Dict[str, Any], linked_pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine content from main page and linked pages."""
        combined_markdown = main_page.get("markdown", "")
        
        # Add linked pages content
        for page in linked_pages:
            page_markdown = page.get("markdown", "")
            if page_markdown:
                combined_markdown += f"\n\n## Content from {page.get('url', '')}\n\n{page_markdown}\n"
        
        return {
            "markdown": combined_markdown,
            "main_page": main_page,
            "linked_pages": linked_pages,
            "total_pages": 1 + len(linked_pages)
        }
    
    def _extract_important_data(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract important information from scraped content."""
        markdown = scraped_data.get("markdown", "")
        main_page = scraped_data.get("main_page", {})
        metadata = main_page.get("metadata", {})
        
        # Extract key sections
        important_data = {
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "keywords": metadata.get("keywords", []),
            "headings": self._extract_headings(markdown),
            "links": self._extract_links(markdown),
            "code_blocks": self._extract_code_blocks(markdown),
            "features": self._extract_features(markdown),
            "api_endpoints_raw": self._extract_api_endpoints(markdown),
            "pricing_mentions": self._extract_pricing_mentions(markdown),
            "tech_stack_mentions": self._extract_tech_mentions(markdown),
        }
        
        return important_data
    
    def _extract_api_endpoints(self, markdown: str) -> list:
        """Extract API endpoint patterns from markdown using regex."""
        # Look for common API endpoint patterns
        patterns = [
            r'`([A-Z]+)\s+([/a-zA-Z0-9\-_]+)`',  # GET /api/v1/endpoint
            r'`([/a-zA-Z0-9\-_/]+)`',  # /api/v1/endpoint
            r'https?://[^\s]+/api/[^\s\)]+',  # Full API URLs
        ]
        
        endpoints = []
        for pattern in patterns:
            matches = re.findall(pattern, markdown)
            endpoints.extend(matches)
        
        return list(set(endpoints))[:30]  # Unique endpoints, limit to 30
    
    def _extract_pricing_mentions(self, markdown: str) -> list:
        """Extract pricing-related content."""
        pricing_keywords = ["price", "cost", "pricing", "plan", "tier", "subscription", "free", "paid"]
        lines = markdown.split("\n")
        
        pricing_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in pricing_keywords):
                pricing_lines.append(line.strip())
        
        return pricing_lines[:20]
    
    def _extract_tech_mentions(self, markdown: str) -> list:
        """Extract technology mentions."""
        # Common tech stack keywords
        tech_keywords = [
            "python", "javascript", "node", "react", "vue", "angular",
            "docker", "kubernetes", "aws", "azure", "gcp", "postgresql",
            "mysql", "mongodb", "redis", "graphql", "rest", "api",
            "typescript", "java", "go", "rust", "ruby", "php"
        ]
        
        mentions = []
        for keyword in tech_keywords:
            if re.search(rf'\b{keyword}\b', markdown, re.IGNORECASE):
                mentions.append(keyword)
        
        return list(set(mentions))  # Unique mentions
    
    def _extract_headings(self, markdown: str) -> list:
        """Extract all headings from markdown."""
        headings = []
        for line in markdown.split("\n"):
            if line.strip().startswith("#"):
                headings.append(line.strip())
        return headings[:20]  # Limit to first 20 headings
    
    def _extract_links(self, markdown: str) -> list:
        """Extract all links from markdown."""
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        links = re.findall(link_pattern, markdown)
        return [{"text": text, "url": url} for text, url in links[:50]]  # Limit to 50 links
    
    def _extract_code_blocks(self, markdown: str) -> list:
        """Extract code blocks from markdown."""
        code_pattern = r'```[\w]*\n(.*?)```'
        code_blocks = re.findall(code_pattern, markdown, re.DOTALL)
        return code_blocks[:10]  # Limit to first 10 code blocks
    
    def _extract_features(self, markdown: str) -> list:
        """Extract feature-like content (bullet points, feature lists)."""
        features = []
        lines = markdown.split("\n")
        
        for i, line in enumerate(lines):
            # Look for bullet points with feature-like keywords
            if line.strip().startswith("-") or line.strip().startswith("*"):
                text = line.strip()[1:].strip()
                if any(keyword in text.lower() for keyword in 
                       ["feature", "support", "include", "provide", "enable", "allow"]):
                    features.append(text)
        
        return features[:20]  # Limit to 20 features
    
    # Note: Analysis methods moved to strategy pattern
    # The analysis is handled by AnalysisStrategy implementations
    # See src/step1/analysis_strategy.py for implementation details
    
    def _generate_intelligent_analysis(self, content: str, extracted_data: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Generate comprehensive analysis using intelligent pattern matching and extraction."""
        title = extracted_data.get("title", "Unknown Product")
        description = extracted_data.get("description", "")
        headings = extracted_data.get("headings", [])
        features = extracted_data.get("features", [])
        links = extracted_data.get("links", [])
        
        # Generate intelligent summary
        summary = self._generate_summary(title, description, content, headings)
        
        # Extract capabilities intelligently
        capabilities = self._extract_capabilities(headings, features, content)
        
        # Generate use cases
        use_cases = self._generate_use_cases(capabilities, title, content)
        
        # Extract technical stack
        technical_stack = self._extract_technical_stack(content, extracted_data)
        
        # Extract integrations
        integrations = self._extract_integrations(content, links)
        
        # Extract API endpoints
        api_endpoints = self._extract_api_endpoints_intelligent(content, links)
        
        # Extract pricing information
        pricing = self._extract_pricing_intelligent(content, headings)
        
        # Determine target audience
        target_audience = self._determine_target_audience(content, title)
        
        # Determine category
        category = self._determine_category(content, url, title)
        
        # Determine deployment
        deployment = self._determine_deployment(content, url)
        
        # Infer underlying algorithm/problem domain (Technical Generalization)
        underlying_algorithm = self._infer_underlying_algorithm(headings, extracted_data.get("code_blocks", []), content)
        
        # Standardize API endpoints to OpenAPI spec fragments (if using LLM)
        api_spec = None
        if api_endpoints and hasattr(self, 'analysis_strategy') and hasattr(self.analysis_strategy, 'llm'):
            api_spec = self._standardize_api_endpoints_to_openapi(api_endpoints, extracted_data.get("api_endpoints_raw", []))
        
        # Build evidence tracking
        evidence_tracking = {
            "technical_facts": [],
            "information_gaps": [],
            "confidence_level": "Medium"
        }
        
        # Add technical facts with evidence
        if api_endpoints:
            evidence_tracking["technical_facts"].append({
                "fact": f"Found {len(api_endpoints)} API endpoints",
                "evidence": f"Extracted from content analysis",
                "confidence": "Medium"
            })
        if technical_stack:
            evidence_tracking["technical_facts"].append({
                "fact": f"Technical stack: {', '.join(technical_stack[:5])}",
                "evidence": f"Found in content analysis",
                "confidence": "Medium"
            })
        
        # Identify gaps
        if not api_endpoints:
            evidence_tracking["information_gaps"].append("No API endpoints found - need API documentation")
        if not api_spec:
            evidence_tracking["information_gaps"].append("No OpenAPI/Swagger spec found - need structured API docs")
        if len(technical_stack) < 3:
            evidence_tracking["information_gaps"].append("Limited technical stack information")
        
        return {
            "summary": summary,
            "capabilities": capabilities,
            "use_cases": use_cases,
            "technical_stack": technical_stack,
            "integrations": integrations,
            "api_endpoints": api_endpoints,
            "api_spec": api_spec,  # OpenAPI spec fragment if available
            "pricing": pricing,
            "target_audience": target_audience,
            "category": category,
            "deployment": deployment,
            "underlying_algorithm": underlying_algorithm,  # Technical DNA
            "evidence_tracking": evidence_tracking,  # Evidence-based tracking
        }
    
    def _generate_summary(self, title: str, description: str, content: str, headings: list) -> str:
        """Generate a comprehensive summary from the product information."""
        # Start with title and description
        summary_parts = []
        
        if title and title != "Unknown Product":
            summary_parts.append(title)
        
        if description:
            summary_parts.append(description[:150])
        
        # Extract key information from content
        content_lower = content.lower()
        
        # Look for key value propositions
        if "all in one" in content_lower or "unified" in content_lower:
            summary_parts.append("Unified platform offering multiple services in one place.")
        
        # Look for main features mentioned early in content
        lines = content.split("\n")[:30]
        for line in lines:
            if len(line.strip()) > 30 and len(line.strip()) < 200:
                if any(keyword in line.lower() for keyword in ["enable", "allow", "provide", "offer", "support"]):
                    summary_parts.append(line.strip()[:150])
                    break
        
        # Combine into summary
        if summary_parts:
            summary = " ".join(summary_parts[:3])  # Max 3 sentences
            return summary[:500]  # Limit length
        
        return f"{title}. A comprehensive platform for users." if title else "Product information extracted from page."
    
    def _extract_capabilities(self, headings: list, features: list, content: str) -> list:
        """Intelligently extract capabilities from headings, features, and content."""
        capabilities = []
        
        # Extract from headings (main sections usually indicate capabilities)
        for heading in headings[:15]:
            heading_clean = heading.replace("#", "").strip()
            if len(heading_clean) > 5 and len(heading_clean) < 100:
                # Clean up common heading patterns
                heading_clean = heading_clean.replace("**", "").strip()
                if heading_clean and heading_clean not in capabilities:
                    capabilities.append(heading_clean)
        
        # Extract from features list
        for feature in features[:15]:
            if feature and len(feature) > 10 and len(feature) < 200:
                # Clean up feature text
                feature_clean = feature.replace("**", "").strip()
                if feature_clean and feature_clean not in capabilities:
                    capabilities.append(feature_clean)
        
        # Extract from content patterns
        content_lower = content.lower()
        capability_patterns = [
            r"supports?\s+([^\.]+)",
            r"enables?\s+([^\.]+)",
            r"allows?\s+([^\.]+)",
            r"provides?\s+([^\.]+)",
            r"offers?\s+([^\.]+)",
        ]
        
        for pattern in capability_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches[:5]:
                if len(match.strip()) > 10 and len(match.strip()) < 150:
                    capabilities.append(match.strip().capitalize())
        
        return list(dict.fromkeys(capabilities))[:20]  # Remove duplicates, limit to 20
    
    def _generate_use_cases(self, capabilities: list, title: str, content: str) -> list:
        """Generate use cases from capabilities and content."""
        use_cases = []
        content_lower = content.lower()
        
        # Generate use cases from capabilities
        for cap in capabilities[:10]:
            if len(cap) > 5:
                # Create use case from capability
                use_case = f"{cap}"
                if "trading" in cap.lower() or "invest" in cap.lower():
                    use_case = "Investors and traders looking for a comprehensive trading platform"
                elif "api" in cap.lower() or "developer" in cap.lower():
                    use_case = "Developers building applications that require API integration"
                elif "data" in cap.lower() or "analytics" in cap.lower():
                    use_case = "Businesses needing data analysis and reporting capabilities"
                
                if use_case not in use_cases:
                    use_cases.append(use_case)
        
        # Extract specific use cases from content
        use_case_keywords = ["for", "use case", "ideal for", "perfect for", "designed for"]
        lines = content.split("\n")
        for line in lines[:50]:
            line_lower = line.lower()
            if any(kw in line_lower for kw in use_case_keywords) and len(line.strip()) > 20:
                use_case = line.strip()[:150]
                if use_case not in use_cases and len(use_cases) < 10:
                    use_cases.append(use_case)
        
        return use_cases[:10]
    
    def _extract_technical_stack(self, content: str, extracted_data: Dict[str, Any]) -> list:
        """Extract technical stack from content."""
        tech_stack = []
        content_lower = content.lower()
        
        # Common tech stack keywords
        tech_keywords = {
            "programming_languages": ["python", "javascript", "typescript", "java", "go", "rust", "ruby", "php", "c++", "c#", "swift", "kotlin"],
            "frameworks": ["react", "vue", "angular", "django", "flask", "express", "spring", "laravel", "rails"],
            "databases": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb"],
            "cloud": ["aws", "azure", "gcp", "google cloud", "amazon web services"],
            "tools": ["docker", "kubernetes", "terraform", "ansible", "jenkins", "git"],
            "apis": ["rest", "graphql", "grpc", "soap"],
            "protocols": ["http", "https", "websocket", "mqtt"]
        }
        
        for category, keywords in tech_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    if keyword not in tech_stack:
                        tech_stack.append(keyword)
        
        # Also use extracted tech mentions
        tech_mentions = extracted_data.get("tech_stack_mentions", [])
        tech_stack.extend([t for t in tech_mentions if t not in tech_stack])
        
        return tech_stack[:15]
    
    def _extract_integrations(self, content: str, links: list) -> list:
        """Extract integrations from content and links."""
        integrations = []
        content_lower = content.lower()
        
        # Common integration keywords
        integration_keywords = ["integrate", "integration", "connect", "plugin", "add-on", "extension", "api", "sdk"]
        
        # Look for integration mentions
        lines = content.split("\n")
        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in integration_keywords):
                # Try to extract integration name
                # Look for common service names
                services = ["stripe", "paypal", "slack", "github", "jira", "salesforce", "zapier", "webhook", "oauth"]
                for service in services:
                    if service in line_lower and service not in integrations:
                        integrations.append(service.capitalize())
        
        # Extract from links (API docs, integration pages)
        for link in links:
            link_text = link.get("text", "").lower()
            link_url = link.get("url", "").lower()
            if any(kw in link_text or kw in link_url for kw in ["integration", "api", "connect", "plugin"]):
                if link_text and link_text not in integrations:
                    integrations.append(link_text[:100])
        
        return integrations[:15]
    
    def _extract_api_endpoints_intelligent(self, content: str, links: list) -> list:
        """Intelligently extract API endpoints using regex patterns."""
        endpoints = []
        
        # Extract from content patterns
        # Common API endpoint patterns
        patterns = [
            r'`([A-Z]+\s+[/a-zA-Z0-9\-_/]+)`',  # GET /api/v1/endpoint
            r'`([/a-zA-Z0-9\-_/]+)`',  # /api/v1/endpoint
            r'https?://[^\s]+/api/[^\s\)]+',  # Full API URLs
            r'/api/v?\d+/[a-zA-Z0-9\-_/]+',  # /api/v1/endpoint
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            endpoints.extend(matches)
        
        # Extract from links (API documentation)
        for link in links:
            url = link.get("url", "")
            text = link.get("text", "")
            if "/api/" in url.lower() or "api" in text.lower():
                if url not in endpoints:
                    endpoints.append(url)
        
        # Clean and deduplicate
        endpoints = list(set(endpoints))[:20]
        return endpoints
    
    def _extract_pricing_intelligent(self, content: str, headings: list) -> Dict[str, Any]:
        """Intelligently extract pricing information."""
        content_lower = content.lower()
        pricing = {
            "model": "unknown",
            "tiers": [],
            "free_tier": "unknown",
            "notes": ""
        }
        
        # Detect pricing model
        if any(kw in content_lower for kw in ["free", "no cost", "complimentary"]):
            if any(kw in content_lower for kw in ["premium", "pro", "paid", "subscription"]):
                pricing["model"] = "freemium"
                pricing["free_tier"] = "true"
            else:
                pricing["model"] = "free"
                pricing["free_tier"] = "true"
        elif any(kw in content_lower for kw in ["subscription", "monthly", "annual", "per month", "per year"]):
            pricing["model"] = "subscription"
        elif any(kw in content_lower for kw in ["one-time", "one time", "lifetime", "perpetual"]):
            pricing["model"] = "one-time"
        elif any(kw in content_lower for kw in ["usage-based", "pay as you go", "per request", "per transaction"]):
            pricing["model"] = "usage-based"
        elif any(kw in content_lower for kw in ["enterprise", "contact sales", "custom pricing"]):
            pricing["model"] = "enterprise"
        
        # Extract pricing tiers
        lines = content.split("\n")
        pricing_keywords = ["$", "€", "£", "price", "cost", "tier", "plan", "pricing", "subscription", "free"]
        
        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in pricing_keywords):
                if len(line.strip()) > 10 and len(line.strip()) < 200:
                    pricing["tiers"].append(line.strip())
        
        # Look for specific pricing mentions in headings
        for heading in headings:
            heading_lower = heading.lower()
            if any(kw in heading_lower for kw in ["price", "pricing", "plan", "tier", "cost"]):
                pricing["tiers"].append(heading.replace("#", "").strip())
        
        pricing["tiers"] = pricing["tiers"][:10]  # Limit to 10 tiers
        
        return pricing
    
    def _determine_target_audience(self, content: str, title: str) -> str:
        """Determine target audience from content."""
        content_lower = content.lower()
        
        if any(kw in content_lower for kw in ["developer", "programmer", "engineer", "technical", "api", "sdk"]):
            return "Developers and technical teams"
        elif any(kw in content_lower for kw in ["business", "enterprise", "company", "organization"]):
            return "Businesses and enterprises"
        elif any(kw in content_lower for kw in ["investor", "trader", "financial", "trading"]):
            return "Investors and traders"
        elif any(kw in content_lower for kw in ["startup", "small business", "sme"]):
            return "Startups and small businesses"
        elif any(kw in content_lower for kw in ["individual", "personal", "consumer"]):
            return "Individual consumers"
        elif any(kw in content_lower for kw in ["marketer", "marketing", "sales"]):
            return "Marketing and sales professionals"
        
        return "General users and businesses"
    
    def _determine_category(self, content: str, url: str, title: str) -> str:
        """Determine product category intelligently."""
        content_lower = content.lower()
        url_lower = url.lower()
        title_lower = title.lower()
        
        # Financial/Trading
        if any(kw in content_lower or kw in title_lower for kw in ["trading", "invest", "stocks", "crypto", "etf", "finance", "broker", "trading platform"]):
            return "Financial Services / Trading Platform"
        
        # API/Developer Tools
        if any(kw in content_lower or kw in url_lower or kw in title_lower for kw in ["api", "developer", "sdk", "integration", "rest api", "graphql"]):
            return "API / Developer Tools"
        
        # Database
        if any(kw in content_lower for kw in ["database", "data storage", "sql", "nosql", "db"]):
            return "Database / Data Storage"
        
        # Analytics
        if any(kw in content_lower for kw in ["analytics", "dashboard", "metrics", "reporting", "bi", "business intelligence"]):
            return "Analytics / Business Intelligence"
        
        # Payment
        if any(kw in content_lower for kw in ["payment", "billing", "invoice", "stripe", "paypal", "checkout"]):
            return "Payment Processing"
        
        # Communication
        if any(kw in content_lower for kw in ["chat", "messaging", "communication", "slack", "email"]):
            return "Communication / Messaging"
        
        # Cloud/Infrastructure
        if any(kw in content_lower for kw in ["cloud", "infrastructure", "hosting", "server", "aws", "azure"]):
            return "Cloud / Infrastructure"
        
        # Security
        if any(kw in content_lower for kw in ["security", "authentication", "auth", "sso", "encryption"]):
            return "Security / Authentication"
        
        # E-commerce
        if any(kw in content_lower for kw in ["ecommerce", "e-commerce", "shop", "store", "cart"]):
            return "E-commerce Platform"
        
        return "Software Platform"
    
    def _determine_deployment(self, content: str, url: str) -> str:
        """Determine deployment model."""
        content_lower = content.lower()
        url_lower = url.lower()
        
        if any(kw in content_lower for kw in ["saas", "software as a service", "cloud-based", "hosted"]):
            return "SaaS"
        elif any(kw in content_lower for kw in ["on-premise", "on-premises", "self-hosted", "self hosted"]):
            return "On-premise"
        elif any(kw in content_lower for kw in ["hybrid", "both cloud and on-premise"]):
            return "Hybrid"
        elif any(kw in content_lower for kw in ["download", "install", "desktop", "mobile app"]):
            return "Client Application"
        
        # Default: most web products are SaaS
        if "http" in url_lower:
            return "SaaS"
        
        return "Unknown"
    
    def _infer_underlying_algorithm(self, headings: list, code_blocks: list, content: str) -> Dict[str, Any]:
        """
        Infer the underlying algorithm or structural problem being solved.
        This extracts the "Technical DNA" - the abstract mathematical/logical pattern.
        
        Returns a dictionary with:
        - problem_type: e.g., "Byzantine Fault Tolerance", "CRUD wrapper", "Graph traversal"
        - complexity: Time/space complexity if inferable
        - pattern: Design pattern or algorithmic approach
        - logic_signature: Input/output constraints and state transitions
        """
        content_lower = content.lower()
        headings_text = " ".join([h.replace("#", "").strip() for h in headings]).lower()
        code_text = " ".join(code_blocks[:3]).lower() if code_blocks else ""
        
        combined_text = f"{headings_text} {code_text} {content_lower[:2000]}"
        
        # Pattern matching for common algorithmic problems
        problem_type = "Unknown"
        complexity = "Unknown"
        pattern = "Unknown"
        logic_signature = {}
        
        # Distributed Systems Patterns
        if any(kw in combined_text for kw in ["consensus", "raft", "paxos", "byzantine", "fault tolerance"]):
            problem_type = "Distributed Consensus / Byzantine Fault Tolerance"
            complexity = "O(n) to O(n²) depending on algorithm"
            pattern = "Consensus Algorithm"
        elif any(kw in combined_text for kw in ["replication", "sharding", "partition"]):
            problem_type = "Data Replication / Partitioning"
            complexity = "O(log n) to O(n) for lookups"
            pattern = "Distributed Data Management"
        
        # Graph/Network Problems
        elif any(kw in combined_text for kw in ["graph", "node", "edge", "traversal", "pathfinding", "shortest path"]):
            problem_type = "Graph Algorithm / Network Analysis"
            complexity = "O(V + E) to O(V²) depending on algorithm"
            pattern = "Graph Traversal / Pathfinding"
        elif any(kw in combined_text for kw in ["matching", "bipartite", "flow"]):
            problem_type = "Graph Matching / Network Flow"
            complexity = "O(VE²) to O(V²E)"
            pattern = "Network Flow Algorithm"
        
        # Search/Indexing
        elif any(kw in combined_text for kw in ["search", "index", "full-text", "elasticsearch", "lucene"]):
            problem_type = "Search / Indexing"
            complexity = "O(log n) for indexed search, O(n) for linear"
            pattern = "Inverted Index / Search Index"
        elif any(kw in combined_text for kw in ["recommendation", "collaborative filtering", "matrix factorization"]):
            problem_type = "Recommendation System"
            complexity = "O(n²) to O(n³) for matrix operations"
            pattern = "Collaborative Filtering / Matrix Factorization"
        
        # Data Processing
        elif any(kw in combined_text for kw in ["stream", "real-time", "event", "kafka", "pipeline"]):
            problem_type = "Stream Processing / Event Sourcing"
            complexity = "O(1) per event, O(n) for batch processing"
            pattern = "Event Stream Processing"
        elif any(kw in combined_text for kw in ["aggregation", "reduce", "map-reduce", "batch"]):
            problem_type = "Data Aggregation / Batch Processing"
            complexity = "O(n) for linear aggregation"
            pattern = "Map-Reduce / Batch Processing"
        
        # Trading/Financial (check first, before other patterns)
        if any(kw in combined_text for kw in ["trading", "order", "matching", "exchange", "market", "invest", "broker", "financial"]):
            problem_type = "Real-time Order Matching / Market Making Engine"
            complexity = "O(n log n) for order matching"
            pattern = "Order Matching Algorithm"
        
        # CRUD/API Wrappers
        elif any(kw in combined_text for kw in ["crud", "rest", "api", "endpoint", "resource"]) and \
             not any(kw in combined_text for kw in ["graph", "complex", "algorithm", "optimization"]):
            problem_type = "CRUD / API Wrapper"
            complexity = "O(1) to O(log n) for database operations"
            pattern = "RESTful API / Resource Management"
        
        # Machine Learning
        elif any(kw in combined_text for kw in ["model", "training", "inference", "neural", "tensor"]):
            problem_type = "Machine Learning / Neural Network"
            complexity = "O(n²) to O(n³) for training, O(n) for inference"
            pattern = "ML Model Training / Inference"
        
        # Extract I/O constraints from code blocks and headings
        if code_blocks:
            # Look for function signatures, type hints, etc.
            for block in code_blocks[:2]:
                # Simple extraction of function signatures
                func_matches = re.findall(r'def\s+(\w+)\s*\([^)]*\)', block)
                if func_matches:
                    logic_signature["functions"] = func_matches[:5]
        
        # Extract state transitions from headings
        state_keywords = ["state", "transition", "status", "stage", "phase"]
        if any(kw in headings_text for kw in state_keywords):
            logic_signature["has_state_machine"] = True
        
        return {
            "problem_type": problem_type,
            "complexity": complexity,
            "pattern": pattern,
            "logic_signature": logic_signature,
            "note": "Inferred from content analysis. For precise analysis, use LLM-based strategy."
        }
    
    def _standardize_api_endpoints_to_openapi(self, api_endpoints: list, raw_endpoints: list) -> Optional[Dict[str, Any]]:
        """
        Use LLM to standardize API endpoints into OpenAPI Specification (OAS) fragments.
        This turns a list of strings into a machine-readable contract.
        
        Returns OpenAPI spec fragment or None if LLM unavailable.
        """
        if not hasattr(self, 'analysis_strategy') or not hasattr(self.analysis_strategy, 'llm'):
            return None
        
        try:
            # Combine endpoints
            all_endpoints = list(set(api_endpoints + raw_endpoints))[:20]
            endpoints_text = "\n".join([f"- {ep}" for ep in all_endpoints[:15]])
            
            prompt = f"""Given the following API endpoint patterns extracted from documentation, 
standardize them into an OpenAPI Specification (OAS) 3.0 fragment.

Endpoints:
{endpoints_text}

Provide a JSON object with the following structure:
{{
    "openapi": "3.0.0",
    "info": {{
        "title": "API Specification",
        "version": "1.0.0"
    }},
    "paths": {{
        // For each endpoint, create a path entry with methods (GET, POST, etc.)
        // Example: "/api/v1/users": {{ "get": {{ "summary": "...", "responses": {{ "200": {{ "description": "..." }} }} }} }}
    }}
}}

Respond ONLY with valid JSON, no additional text."""

            # Try to use LLM if available
            if hasattr(self.analysis_strategy, 'llm') and self.analysis_strategy.llm:
                # This would need to be implemented in the strategy
                # For now, return a basic structure
                return {
                    "openapi": "3.0.0",
                    "info": {"title": "API Specification", "version": "1.0.0"},
                    "paths": {ep: {"get": {"summary": f"Endpoint: {ep}"}} for ep in all_endpoints[:10]},
                    "note": "Basic structure. Use LLM strategy for full OpenAPI generation."
                }
        except Exception as e:
            logger.warning(f"Could not standardize API endpoints: {str(e)}")
        
        return None
    
    def _generate_fallback_analysis(self, content: str, title: str, url: str) -> Dict[str, Any]:
        """Generate basic analysis from extracted data when LLM fails."""
        # Extract basic info from content
        lines = content.split("\n")
        headings = [line.strip() for line in lines if line.strip().startswith("#")][:20]
        features = [line.strip()[1:].strip() for line in lines 
                   if (line.strip().startswith("-") or line.strip().startswith("*")) 
                   and len(line.strip()) > 10][:20]
        
        description = ""
        for line in lines[:50]:
            if len(line.strip()) > 50 and not line.strip().startswith("#"):
                description = line.strip()[:200]
                break
        
        # Create summary from title and description
        summary = f"{title}. {description}" if description else title
        
        # Extract capabilities from headings and features
        capabilities = []
        for heading in headings[:10]:
            if heading and len(heading) > 3:
                capabilities.append(heading.replace("#", "").strip())
        capabilities.extend(features[:10])
        
        # Try to infer category from URL and content
        category = "Unknown"
        url_lower = url.lower()
        content_lower = content.lower()
        
        if any(kw in content_lower for kw in ["trading", "invest", "stocks", "crypto", "etf", "finance", "broker"]):
            category = "Financial Services / Trading Platform"
        elif any(kw in content_lower for kw in ["api", "developer", "sdk", "integration"]):
            category = "API / Developer Tools"
        elif any(kw in content_lower for kw in ["database", "data storage", "sql"]):
            category = "Database / Data Storage"
        elif any(kw in content_lower for kw in ["analytics", "dashboard", "metrics", "reporting"]):
            category = "Analytics / Business Intelligence"
        elif any(kw in content_lower for kw in ["payment", "billing", "invoice", "stripe", "paypal"]):
            category = "Payment Processing"
        elif "api" in url_lower or "docs" in url_lower:
            category = "API / Developer Tools"
        
        # Extract tech stack mentions from content
        tech_keywords = ["python", "javascript", "react", "node", "docker", "aws", "api", "rest", "graphql"]
        tech_stack = [kw for kw in tech_keywords if kw in content.lower()]
        
        # Extract pricing mentions from content
        pricing_keywords = ["free", "price", "cost", "subscription", "tier", "plan"]
        pricing_mentions = [line.strip() for line in lines 
                           if any(kw in line.lower() for kw in pricing_keywords)][:10]
        pricing_model = "unknown"
        if any("free" in str(m).lower() for m in pricing_mentions):
            pricing_model = "freemium"
        elif any("subscription" in str(m).lower() or "monthly" in str(m).lower() for m in pricing_mentions):
            pricing_model = "subscription"
        
        return {
            "summary": summary[:500],  # Limit summary length
            "capabilities": capabilities[:15],
            "use_cases": [f"Use {title} for {cap}" for cap in capabilities[:5]],
            "technical_stack": tech_stack,
            "integrations": [],
            "api_endpoints": [],  # Would need more sophisticated extraction
            "pricing": {
                "model": pricing_model,
                "tiers": pricing_mentions[:5],
                "free_tier": "unknown",
                "notes": "Pricing information extracted from page content"
            },
            "target_audience": "Users interested in the product category",
            "category": category,
            "deployment": "SaaS",  # Most web products are SaaS
            "fallback_analysis": True,
            "note": "This is a fallback analysis generated from extracted data. LLM analysis was unavailable."
        }
    
    def save_output(self, result: Dict[str, Any], output_file: Optional[str] = None, 
                   format: str = "markdown") -> str:
        """
        Save analysis results to a file.
        
        Args:
            result: Analysis result dictionary
            output_file: Optional output file path. If None, generates filename from URL.
            format: Output format - "markdown" or "json" (default: "markdown")
        
        Returns:
            Path to saved file
        """
        if output_file is None:
            # Generate filename from URL
            url = result.get("url", "unknown")
            domain = url.replace("https://", "").replace("http://", "").split("/")[0]
            domain = domain.replace(".", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = "md" if format == "markdown" else "json"
            output_file = f"outputs/step1_{domain}_{timestamp}.{extension}"
        
        import os
        os.makedirs(os.path.dirname(output_file) if "/" in output_file else "outputs", exist_ok=True)
        
        if format == "markdown":
            markdown_content = self._generate_markdown_report(result)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
        else:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def _generate_markdown_report(self, result: Dict[str, Any]) -> str:
        """Generate a markdown report from analysis results."""
        url = result.get("url", "Unknown")
        analysis = result.get("analysis", {})
        extracted = result.get("extracted_data", {})
        
        markdown = f"""# Product Analysis Report

**URL:** {url}  
**Analyzed:** {result.get('timestamp', 'Unknown')}  
**Pages Analyzed:** {result.get('main_page', {}).get('url', 'N/A')} + {len(result.get('linked_pages', []))} linked pages

---

## Summary

{analysis.get('summary', 'No summary available')}

---

## Product Information

**Category:** {analysis.get('category', 'Unknown')}  
**Target Audience:** {analysis.get('target_audience', 'Unknown')}  
**Deployment:** {analysis.get('deployment', 'Unknown')}

---

## Capabilities

"""
        
        capabilities = analysis.get('capabilities', [])
        if capabilities:
            for cap in capabilities:
                markdown += f"- {cap}\n"
        else:
            markdown += "*No capabilities listed*\n"
        
        markdown += "\n---\n\n## Use Cases\n\n"
        use_cases = analysis.get('use_cases', [])
        if use_cases:
            for use_case in use_cases:
                markdown += f"- {use_case}\n"
        else:
            markdown += "*No use cases listed*\n"
        
        markdown += "\n---\n\n## Technical Stack\n\n"
        tech_stack = analysis.get('technical_stack', [])
        if tech_stack:
            for tech in tech_stack:
                markdown += f"- {tech}\n"
        else:
            markdown += "*No technical stack information available*\n"
        
        markdown += "\n---\n\n## Integrations\n\n"
        integrations = analysis.get('integrations', [])
        if integrations:
            for integration in integrations:
                markdown += f"- {integration}\n"
        else:
            markdown += "*No integrations listed*\n"
        
        markdown += "\n---\n\n## API Endpoints\n\n"
        api_endpoints = analysis.get('api_endpoints', [])
        if api_endpoints:
            for endpoint in api_endpoints:
                markdown += f"- `{endpoint}`\n"
        else:
            markdown += "*No API endpoints found*\n"
        
        markdown += "\n---\n\n## Pricing\n\n"
        pricing = analysis.get('pricing', {})
        markdown += f"**Model:** {pricing.get('model', 'Unknown')}\n\n"
        
        if pricing.get('free_tier', 'unknown') != 'unknown':
            markdown += f"**Free Tier:** {pricing.get('free_tier', 'Unknown')}\n\n"
        
        tiers = pricing.get('tiers', [])
        if tiers:
            markdown += "**Pricing Tiers:**\n"
            for tier in tiers:
                markdown += f"- {tier}\n"
        
        if pricing.get('notes'):
            markdown += f"\n**Notes:** {pricing.get('notes')}\n"
        
        markdown += "\n---\n\n## Extracted Data\n\n"
        markdown += f"**Title:** {extracted.get('title', 'Unknown')}\n\n"
        markdown += f"**Description:** {extracted.get('description', 'No description')}\n\n"
        
        headings = extracted.get('headings', [])
        if headings:
            markdown += "### Key Headings\n\n"
            for heading in headings[:10]:
                markdown += f"{heading}\n"
        
        markdown += "\n---\n\n*Report generated by SynchroB Step 1*"
        
        return markdown
