"""
Discovery orchestrator — runs all sources in priority phases and collects results.

Phase 1 (Baseline, no URL needed): LLM Knowledge + Package Registry
Phase 2 (URL-dependent): OpenAPI Spec Probe + GitHub Repo Analysis
Phase 3 (Targeted fill): Web Scraping using discovered doc/API URLs
"""

import logging
from typing import Dict, List, Optional

from src.discovery.models import SourceType, SourceResult
from src.discovery.llm_knowledge import LLMKnowledgeDiscovery
from src.discovery.package_registry import PackageRegistryDiscovery
from src.discovery.openapi_discovery import OpenAPIDiscovery
from src.discovery.github_discovery import GitHubDiscovery
from src.discovery.web_scraping import WebScrapingDiscovery

logger = logging.getLogger(__name__)


class DiscoveryOrchestrator:
    """Runs all discovery sources in phased order and collects results."""

    def __init__(
        self,
        gemini_client=None,
        openai_client=None,
        firecrawl_client=None,
        github_token: Optional[str] = None,
    ):
        self.llm_source = LLMKnowledgeDiscovery(
            gemini_client=gemini_client,
            openai_client=openai_client,
        )
        self.package_source = PackageRegistryDiscovery()
        self.openapi_source = OpenAPIDiscovery()
        self.github_source = GitHubDiscovery(token=github_token)
        self.web_source = WebScrapingDiscovery(firecrawl_client=firecrawl_client)

    def run_discovery(
        self,
        product_name: str,
        product_url: Optional[str] = None,
        crawl_depth: int = 1,
    ) -> List[SourceResult]:
        """
        Execute the multi-source discovery pipeline.

        Execution order matters — later phases use URLs discovered by earlier phases.

        Returns:
            List of SourceResult (one per source attempted, including failures)
        """
        results: List[SourceResult] = []
        discovered_urls: Dict[str, str] = {}

        if product_url:
            discovered_urls["product_url"] = product_url

        # ── Phase 1: Baseline (no URL required) ──────────────────────
        print(f"  🔍 Phase 1: Baseline discovery for '{product_name}'...")

        llm_result = self._run_safe(
            "LLM Knowledge",
            SourceType.LLM_KNOWLEDGE,
            lambda: self.llm_source.discover(product_name, product_url=product_url),
        )
        results.append(llm_result)
        self._collect_urls(llm_result, discovered_urls)

        pkg_result = self._run_safe(
            "Package Registry",
            SourceType.PACKAGE_REGISTRY,
            lambda: self.package_source.discover(product_name),
        )
        results.append(pkg_result)
        self._collect_urls(pkg_result, discovered_urls)

        # ── Phase 2: URL-dependent discovery ─────────────────────────
        base_url = (
            product_url
            or discovered_urls.get("product_url")
            or discovered_urls.get("homepage")
        )

        if base_url:
            # Build list of URLs to probe (base + api subdomain)
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

            openapi_found = False
            for probe_url in probe_urls:
                print(f"  🔍 Phase 2: Probing {probe_url} for OpenAPI specs...")
                openapi_result = self._run_safe(
                    "OpenAPI Spec",
                    SourceType.OPENAPI_SPEC,
                    lambda url=probe_url: self.openapi_source.discover(url),
                )
                results.append(openapi_result)
                self._collect_urls(openapi_result, discovered_urls)
                if openapi_result.success:
                    openapi_found = True
                    break  # Found a spec, no need to probe more URLs
        else:
            print("  ⚠️  Phase 2: No product URL available — skipping OpenAPI probe")

        github_url = discovered_urls.get("github_repo")
        if github_url:
            print(f"  🔍 Phase 2: Analyzing GitHub repo {github_url}...")
            gh_result = self._run_safe(
                "GitHub Repo",
                SourceType.GITHUB_REPO,
                lambda: self.github_source.discover(github_url),
            )
            results.append(gh_result)
            self._collect_urls(gh_result, discovered_urls)
        else:
            print("  ⚠️  Phase 2: No GitHub repo URL discovered — skipping")

        # ── Phase 3: Targeted web scraping ───────────────────────────
        scrape_url = base_url or discovered_urls.get("homepage")
        target_urls = self._collect_target_urls(discovered_urls)

        if scrape_url or target_urls:
            print(
                f"  🔍 Phase 3: Targeted web scraping"
                f" ({len(target_urls)} discovered doc URLs)..."
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
            print("  ⚠️  Phase 3: No URL available — skipping web scraping")

        # ── Summary ──────────────────────────────────────────────────
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        print(
            f"  ✅ Discovery complete: {success_count}/{total_count} sources succeeded"
        )

        if success_count == 0:
            print("  ❌ WARNING: All discovery sources failed!")

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
                print(f"    ✓ {label}: {caps} capabilities, {eps} endpoints")
            else:
                print(f"    ✗ {label}: {result.error or 'no data found'}")
            return result
        except Exception as exc:
            logger.exception("Source %s raised unexpected error", label)
            print(f"    ✗ {label}: ERROR — {exc}")
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
