"""
Source merger for the multi-source discovery pipeline.

Merges results from all discovery sources into a single unified result,
handling deduplication, confidence upgrades, and source weighting.
"""

from typing import List, Dict, Optional

from src.discovery.models import (
    SourceType,
    ConfidenceLevel,
    SourcedFact,
    SourcedEndpoint,
    SourceResult,
    MergedDiscoveryResult,
)


# Weight assigned to each source type.
# Higher weight = more authoritative and preferred when deduplicating.
SOURCE_WEIGHTS: Dict[SourceType, int] = {
    SourceType.OPENAPI_SPEC: 95,
    SourceType.LOCAL_REPO: 90,
    SourceType.GITHUB_REPO: 80,
    SourceType.PACKAGE_REGISTRY: 75,
    SourceType.WEB_SCRAPE: 40,
    SourceType.LLM_KNOWLEDGE: 30,
}

# Confidence ordering for sorting (higher index = higher confidence)
_CONFIDENCE_ORDER = {
    ConfidenceLevel.LOW: 0,
    ConfidenceLevel.MEDIUM: 1,
    ConfidenceLevel.HIGH: 2,
}


class SourceMerger:
    """
    Merges multiple SourceResult objects into a single MergedDiscoveryResult.

    Handles:
    - Deduplication of facts and endpoints across sources
    - Confidence upgrades when a fact is corroborated by multiple sources
    - Weighted source selection (authoritative sources preferred)
    - Combined content assembly in weight order
    """

    def merge(
        self, results: List[SourceResult], product_name: str
    ) -> MergedDiscoveryResult:
        """
        Merge all source results into a unified discovery result.

        Args:
            results: List of SourceResult objects from individual discovery sources.
            product_name: The canonical product name for the merged result.

        Returns:
            MergedDiscoveryResult containing deduplicated, weighted data.
        """
        # ------------------------------------------------------------------
        # 1. Separate successful vs failed results
        # ------------------------------------------------------------------
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        sources_used = [r.source_type for r in successful]
        sources_failed = [
            {"source": r.source_type.value, "error": r.error or "Unknown error"}
            for r in failed
        ]

        # ------------------------------------------------------------------
        # 2. Determine product_url (prefer web_scrape or openapi_spec)
        # ------------------------------------------------------------------
        product_url = self._pick_product_url(successful)

        # ------------------------------------------------------------------
        # 3. Determine description (prefer highest-weight source)
        # ------------------------------------------------------------------
        description = self._pick_description(successful)

        # ------------------------------------------------------------------
        # 4. Resolve openapi_spec dict
        # ------------------------------------------------------------------
        openapi_spec = self._pick_openapi_spec(successful)

        # ------------------------------------------------------------------
        # 5. Merge and deduplicate list fields
        # ------------------------------------------------------------------
        capabilities = self._deduplicate_facts(
            self._collect_facts(successful, "capabilities")
        )
        api_endpoints = self._deduplicate_endpoints(
            self._collect_endpoints(successful)
        )
        auth_methods = self._deduplicate_facts(
            self._collect_facts(successful, "auth_methods")
        )
        sdk_languages = self._deduplicate_facts(
            self._collect_facts(successful, "sdk_languages")
        )
        dependencies = self._deduplicate_facts(
            self._collect_facts(successful, "dependencies")
        )
        integrations = self._deduplicate_facts(
            self._collect_facts(successful, "integrations")
        )
        technical_stack = self._deduplicate_facts(
            self._collect_facts(successful, "technical_stack")
        )
        architecture_patterns = self._deduplicate_facts(
            self._collect_facts(successful, "architecture_patterns")
        )
        deployment_options = self._deduplicate_facts(
            self._collect_facts(successful, "deployment_options")
        )

        # ------------------------------------------------------------------
        # 6. Build combined_content (highest weight first)
        # ------------------------------------------------------------------
        combined_content = self._build_combined_content(successful)

        # ------------------------------------------------------------------
        # 7. Compute overall confidence and source coverage
        # ------------------------------------------------------------------
        overall_confidence = self._compute_overall_confidence(successful)
        source_coverage = {st.value: (st in sources_used) for st in SourceType}

        return MergedDiscoveryResult(
            product_name=product_name,
            product_url=product_url,
            sources_used=sources_used,
            sources_failed=sources_failed,
            capabilities=capabilities,
            api_endpoints=api_endpoints,
            openapi_spec=openapi_spec,
            auth_methods=auth_methods,
            sdk_languages=sdk_languages,
            dependencies=dependencies,
            integrations=integrations,
            technical_stack=technical_stack,
            architecture_patterns=architecture_patterns,
            deployment_options=deployment_options,
            description=description,
            combined_content=combined_content,
            overall_confidence=overall_confidence,
            source_coverage=source_coverage,
        )

    # ------------------------------------------------------------------
    # Fact deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate_facts(facts: List[SourcedFact]) -> List[SourcedFact]:
        """
        Deduplicate a list of SourcedFact objects.

        Rules:
        1. Group by normalized value (lowercase, stripped).
        2. If a fact appears from 2+ distinct sources, upgrade confidence to HIGH.
        3. Keep the version from the highest-weight source.
        4. Sort by confidence (HIGH first), then by source weight descending.

        Returns:
            Deduplicated and sorted list of SourcedFact.
        """
        if not facts:
            return []

        # Group by normalized value
        groups: Dict[str, List[SourcedFact]] = {}
        for fact in facts:
            key = fact.value.strip().lower()
            groups.setdefault(key, []).append(fact)

        deduplicated: List[SourcedFact] = []
        for _key, group in groups.items():
            # Determine distinct sources in this group
            distinct_sources = {f.source for f in group}

            # Pick the representative from the highest-weight source
            best = max(group, key=lambda f: SOURCE_WEIGHTS.get(f.source, 0))

            # If corroborated by 2+ sources, upgrade to HIGH
            if len(distinct_sources) >= 2:
                best = best.model_copy(update={"confidence": ConfidenceLevel.HIGH})

            deduplicated.append(best)

        # Sort: HIGH confidence first, then by source weight descending
        deduplicated.sort(
            key=lambda f: (
                -_CONFIDENCE_ORDER.get(f.confidence, 0),
                -SOURCE_WEIGHTS.get(f.source, 0),
            )
        )

        return deduplicated

    # ------------------------------------------------------------------
    # Endpoint deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate_endpoints(
        endpoints: List[SourcedEndpoint],
    ) -> List[SourcedEndpoint]:
        """
        Deduplicate a list of SourcedEndpoint objects.

        Rules:
        1. Group by (method_upper, normalized_path) where normalized_path is
           lowercase with trailing slash stripped.
        2. For each group, keep the most complete version (prefer the one
           with parameters, summary, response_schema, etc.).
        3. If from 2+ distinct sources, upgrade confidence to HIGH.
        4. Sort by path alphabetically.

        Returns:
            Deduplicated and sorted list of SourcedEndpoint.
        """
        if not endpoints:
            return []

        # Group by (method, normalized path)
        groups: Dict[tuple, List[SourcedEndpoint]] = {}
        for ep in endpoints:
            method_key = (ep.method or "").upper()
            path_key = ep.path.strip().lower().rstrip("/")
            key = (method_key, path_key)
            groups.setdefault(key, []).append(ep)

        deduplicated: List[SourcedEndpoint] = []
        for _key, group in groups.items():
            distinct_sources = {ep.source for ep in group}

            # Score completeness: prefer endpoints with more populated fields
            def _completeness(ep: SourcedEndpoint) -> int:
                score = 0
                if ep.summary:
                    score += 2
                if ep.parameters:
                    score += 3
                if ep.response_schema:
                    score += 2
                if ep.auth_required is not None:
                    score += 1
                # Prefer higher-weight sources as tiebreaker
                score += SOURCE_WEIGHTS.get(ep.source, 0) // 10
                return score

            best = max(group, key=_completeness)

            # If corroborated by 2+ sources, upgrade confidence
            if len(distinct_sources) >= 2:
                best = best.model_copy(update={"confidence": ConfidenceLevel.HIGH})

            deduplicated.append(best)

        # Sort alphabetically by path
        deduplicated.sort(key=lambda ep: ep.path.lower())

        return deduplicated

    # ------------------------------------------------------------------
    # Confidence computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_overall_confidence(
        results: List[SourceResult],
    ) -> ConfidenceLevel:
        """
        Compute overall confidence level from successful source results.

        - If any OPENAPI_SPEC or GITHUB_REPO source succeeded -> HIGH
        - If 2+ sources succeeded -> MEDIUM
        - Otherwise -> LOW
        """
        if not results:
            return ConfidenceLevel.LOW

        source_types = {r.source_type for r in results}

        high_authority = {SourceType.OPENAPI_SPEC, SourceType.GITHUB_REPO, SourceType.LOCAL_REPO}
        if source_types & high_authority:
            return ConfidenceLevel.HIGH

        if len(results) >= 2:
            return ConfidenceLevel.MEDIUM

        return ConfidenceLevel.LOW

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pick_product_url(successful: List[SourceResult]) -> Optional[str]:
        """Pick product_url, preferring web_scrape or openapi_spec sources."""
        preferred_sources = [SourceType.WEB_SCRAPE, SourceType.OPENAPI_SPEC]

        # Try preferred sources first
        for src_type in preferred_sources:
            for r in successful:
                if r.source_type == src_type and r.product_url:
                    return r.product_url

        # Fall back to any source
        for r in successful:
            if r.product_url:
                return r.product_url

        return None

    @staticmethod
    def _pick_description(successful: List[SourceResult]) -> Optional[str]:
        """Pick description from the highest-weight source that has one."""
        candidates = [
            r for r in successful if r.description
        ]
        if not candidates:
            return None

        best = max(
            candidates,
            key=lambda r: SOURCE_WEIGHTS.get(r.source_type, 0),
        )
        return best.description

    @staticmethod
    def _pick_openapi_spec(
        successful: List[SourceResult],
    ) -> Optional[Dict]:
        """
        Pick openapi_spec: prefer OPENAPI_SPEC source, fallback to GITHUB_REPO.
        """
        # Try OPENAPI_SPEC source first
        for r in successful:
            if r.source_type == SourceType.OPENAPI_SPEC and r.openapi_spec:
                return r.openapi_spec

        # Fallback to GITHUB_REPO if it discovered a spec
        for r in successful:
            if r.source_type == SourceType.GITHUB_REPO and r.openapi_spec:
                return r.openapi_spec

        return None

    @staticmethod
    def _collect_facts(
        successful: List[SourceResult], field_name: str
    ) -> List[SourcedFact]:
        """Collect all facts from a named field across all successful results."""
        all_facts: List[SourcedFact] = []
        for r in successful:
            facts = getattr(r, field_name, [])
            if facts:
                all_facts.extend(facts)
        return all_facts

    @staticmethod
    def _collect_endpoints(
        successful: List[SourceResult],
    ) -> List[SourcedEndpoint]:
        """Collect all endpoints across all successful results."""
        all_endpoints: List[SourcedEndpoint] = []
        for r in successful:
            if r.api_endpoints:
                all_endpoints.extend(r.api_endpoints)
        return all_endpoints

    @staticmethod
    def _build_combined_content(successful: List[SourceResult]) -> str:
        """
        Concatenate raw_content from all sources in weight order (highest first).
        """
        # Sort by weight descending
        ordered = sorted(
            successful,
            key=lambda r: SOURCE_WEIGHTS.get(r.source_type, 0),
            reverse=True,
        )

        parts: List[str] = []
        for r in ordered:
            if r.raw_content:
                header = f"=== Source: {r.source_type.value} ==="
                parts.append(f"{header}\n{r.raw_content}")

        return "\n\n".join(parts)
