"""
Discovery orchestrator — runs all sources in priority phases and collects results.

Phase 0 (optional): Local Repo Analysis — clone, extract, LLM-analyze source code
Phase 1 (Baseline, no URL needed): LLM Knowledge + Package Registry
Phase 2 (URL-dependent): OpenAPI Spec Probe + GitHub Repo Analysis
Phase 3 (Targeted fill): Web Scraping using discovered doc/API URLs
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from src.discovery.models import SourceType, SourceResult
from src.discovery.llm_knowledge import LLMKnowledgeDiscovery
from src.discovery.package_registry import PackageRegistryDiscovery
from src.discovery.openapi_discovery import OpenAPIDiscovery
from src.discovery.github_discovery import GitHubDiscovery
from src.discovery.web_scraping import WebScrapingDiscovery
from src.discovery.local_repo_discovery import LocalRepoDiscovery

logger = logging.getLogger(__name__)


class DiscoveryOrchestrator:
    """Runs all discovery sources in phased order and collects results."""

    def __init__(
        self,
        claude_client=None,
        gemini_client=None,
        openai_client=None,
        firecrawl_client=None,
        github_token: Optional[str] = None,
    ):
        self.llm_source = LLMKnowledgeDiscovery(
            claude_client=claude_client,
            gemini_client=gemini_client,
            openai_client=openai_client,
        )
        self.package_source = PackageRegistryDiscovery()
        self.openapi_source = OpenAPIDiscovery()
        self.github_source = GitHubDiscovery(token=github_token)
        self.web_source = WebScrapingDiscovery(firecrawl_client=firecrawl_client)
        self.local_repo_source = LocalRepoDiscovery(
            claude_client=claude_client,
            gemini_client=gemini_client,
            openai_client=openai_client,
        )

    def run_discovery(
        self,
        product_name: str,
        product_url: Optional[str] = None,
        crawl_depth: int = 1,
        github_url: Optional[str] = None,
    ) -> List[SourceResult]:
        """
        Execute the multi-source discovery pipeline.

        Execution order matters — later phases use URLs discovered by earlier phases.
        Within phases, independent sources run concurrently.

        Args:
            product_name: Name of the product to discover
            product_url: Optional product website URL
            crawl_depth: Web scraping crawl depth
            github_url: Optional GitHub repo URL for local clone-based analysis

        Returns:
            List of SourceResult (one per source attempted, including failures)
        """
        results: List[SourceResult] = []
        discovered_urls: Dict[str, str] = {}

        if product_url:
            discovered_urls["product_url"] = product_url
        if github_url:
            discovered_urls["github_repo"] = github_url

        # ── Phase 0 (optional): Local repo analysis ──
        if github_url:
            logger.info("Phase 0: Local repo analysis for '%s'...", github_url)
            local_result = self._run_safe(
                "Local Repo",
                SourceType.LOCAL_REPO,
                lambda: self.local_repo_source.discover(github_url),
            )
            results.append(local_result)
            self._collect_urls(local_result, discovered_urls)

        # ── Phase 1: Baseline (no URL required) — run in parallel ──
        logger.info("Phase 1: Baseline discovery for '%s'...", product_name)

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_llm = executor.submit(
                self._run_safe,
                "LLM Knowledge",
                SourceType.LLM_KNOWLEDGE,
                lambda: self.llm_source.discover(product_name, product_url=product_url),
            )
            future_pkg = executor.submit(
                self._run_safe,
                "Package Registry",
                SourceType.PACKAGE_REGISTRY,
                lambda: self.package_source.discover(product_name),
            )

            llm_result = future_llm.result()
            pkg_result = future_pkg.result()

        results.append(llm_result)
        self._collect_urls(llm_result, discovered_urls)
        results.append(pkg_result)
        self._collect_urls(pkg_result, discovered_urls)

        # ── Phase 2: URL-dependent discovery — OpenAPI + GitHub in parallel ──
        base_url = (
            product_url
            or discovered_urls.get("product_url")
            or discovered_urls.get("homepage")
        )

        phase2_futures = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            # OpenAPI probing
            if base_url:
                probe_urls = [base_url]
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url if "://" in base_url else f"https://{base_url}")
                    host = parsed.hostname or ""
                    if host and not host.startswith("api."):
                        api_variant = f"{parsed.scheme}://api.{host}"
                        probe_urls.append(api_variant)
                except Exception:
                    pass

                # Submit OpenAPI probe (tries first URL)
                phase2_futures["openapi"] = executor.submit(
                    self._probe_openapi_urls, probe_urls
                )
            else:
                logger.info("Phase 2: No product URL available — skipping OpenAPI probe")

            # GitHub analysis
            github_url = discovered_urls.get("github_repo")
            if github_url:
                phase2_futures["github"] = executor.submit(
                    self._run_safe,
                    "GitHub Repo",
                    SourceType.GITHUB_REPO,
                    lambda: self.github_source.discover(github_url),
                )
            else:
                logger.info("Phase 2: No GitHub repo URL discovered — skipping")

            # Collect phase 2 results
            if "openapi" in phase2_futures:
                openapi_results = phase2_futures["openapi"].result()
                results.extend(openapi_results)
                for r in openapi_results:
                    self._collect_urls(r, discovered_urls)

            if "github" in phase2_futures:
                gh_result = phase2_futures["github"].result()
                results.append(gh_result)
                self._collect_urls(gh_result, discovered_urls)

        # ── Phase 3: Targeted web scraping (sequential, depends on earlier phases) ──
        scrape_url = base_url or discovered_urls.get("homepage")
        target_urls = self._collect_target_urls(discovered_urls)

        if scrape_url or target_urls:
            logger.info(
                "Phase 3: Targeted web scraping (%d discovered doc URLs)...",
                len(target_urls),
            )
            scrape_result = self._run_safe(
                "Web Scraping",
                SourceType.WEB_SCRAPE,
                lambda: self.web_source.discover(
                    url=scrape_url or target_urls[0],
                    crawl_depth=crawl_depth,
                    target_urls=target_urls,
                ),
            )
            results.append(scrape_result)
        else:
            logger.info("Phase 3: No URL available — skipping web scraping")

        # ── Summary ──────────────────────────────────────────────────
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        logger.info(
            "Discovery complete: %d/%d sources succeeded",
            success_count,
            total_count,
        )

        if success_count == 0:
            logger.warning("All discovery sources failed!")

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _probe_openapi_urls(self, probe_urls: List[str]) -> List[SourceResult]:
        """Probe multiple URLs for OpenAPI specs, stop at first success."""
        results = []
        for probe_url in probe_urls:
            logger.info("Phase 2: Probing %s for OpenAPI specs...", probe_url)
            openapi_result = self._run_safe(
                "OpenAPI Spec",
                SourceType.OPENAPI_SPEC,
                lambda url=probe_url: self.openapi_source.discover(url),
            )
            results.append(openapi_result)
            if openapi_result.success:
                break  # Found a spec, no need to probe more
        return results

    @staticmethod
    def _run_safe(
        label: str,
        source_type: SourceType,
        fn,
    ) -> SourceResult:
        """Run a discovery source with full exception handling."""
        try:
            result = fn()
            if result.success:
                # Count useful data
                caps = len(result.capabilities)
                eps = len(result.api_endpoints)
                logger.info("✓ %s: %d capabilities, %d endpoints", label, caps, eps)
            else:
                logger.info("✗ %s: %s", label, result.error or "no data found")
            return result
        except Exception as exc:
            logger.exception("Source %s raised unexpected error", label)
            return SourceResult(
                source_type=source_type,
                success=False,
                error=str(exc),
            )

    @staticmethod
    def _collect_urls(result: SourceResult, urls: Dict[str, str]) -> None:
        """Merge discovered URLs from a source into the shared URL pool."""
        if result.success and result.discovered_urls:
            for key, url in result.discovered_urls.items():
                if url and key not in urls:
                    urls[key] = url

    @staticmethod
    def _collect_target_urls(discovered_urls: Dict[str, str]) -> List[str]:
        """Collect all discovered documentation/API URLs for targeted scraping."""
        target_keys = {"docs", "api_docs", "documentation", "developer_docs"}
        targets = []
        for key, url in discovered_urls.items():
            if key in target_keys and url:
                targets.append(url)
        return targets
