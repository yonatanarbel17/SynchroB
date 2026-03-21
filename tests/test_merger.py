"""
Tests for src/discovery/merger.py
"""

import pytest
from datetime import datetime
from src.discovery.models import (
    SourceType,
    ConfidenceLevel,
    SourcedFact,
    SourcedEndpoint,
    SourceResult,
)
from src.discovery.merger import SourceMerger


class TestDeduplicateFacts:
    """Test SourceMerger._deduplicate_facts method."""

    def test_deduplicate_duplicate_facts_from_different_sources(self):
        """Test that duplicate facts from 2+ sources get HIGH confidence."""
        merger = SourceMerger()

        facts = [
            SourcedFact(
                value="REST API",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
            SourcedFact(
                value="rest api",  # Different case
                source=SourceType.GITHUB_REPO,
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]

        deduped = merger._deduplicate_facts(facts)

        assert len(deduped) == 1
        assert deduped[0].value == "REST API"
        assert deduped[0].confidence == ConfidenceLevel.HIGH

    def test_deduplicate_unique_facts_remain_unchanged(self):
        """Test that unique facts are not deduplicated."""
        merger = SourceMerger()

        facts = [
            SourcedFact(
                value="Handles JSON",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
            SourcedFact(
                value="Handles XML",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
        ]

        deduped = merger._deduplicate_facts(facts)

        assert len(deduped) == 2

    def test_deduplicate_empty_list(self):
        """Test that empty list returns empty list."""
        merger = SourceMerger()
        deduped = merger._deduplicate_facts([])
        assert deduped == []

    def test_deduplicate_sorts_by_confidence(self):
        """Test that results are sorted by confidence (HIGH first)."""
        merger = SourceMerger()

        facts = [
            SourcedFact(
                value="low confidence",
                source=SourceType.LLM_KNOWLEDGE,
                confidence=ConfidenceLevel.LOW,
            ),
            SourcedFact(
                value="high confidence",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
            SourcedFact(
                value="medium confidence",
                source=SourceType.GITHUB_REPO,
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]

        deduped = merger._deduplicate_facts(facts)

        assert len(deduped) == 3
        assert deduped[0].confidence == ConfidenceLevel.HIGH
        assert deduped[1].confidence == ConfidenceLevel.MEDIUM
        assert deduped[2].confidence == ConfidenceLevel.LOW

    def test_deduplicate_same_source_multiple_times(self):
        """Test that same fact from same source once doesn't boost confidence."""
        merger = SourceMerger()

        facts = [
            SourcedFact(
                value="caching",
                source=SourceType.GITHUB_REPO,
                confidence=ConfidenceLevel.MEDIUM,
            ),
            SourcedFact(
                value="caching",
                source=SourceType.GITHUB_REPO,
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]

        deduped = merger._deduplicate_facts(facts)

        assert len(deduped) == 1
        # Should remain MEDIUM because it's only from 1 distinct source
        assert deduped[0].confidence == ConfidenceLevel.MEDIUM


class TestDeduplicateEndpoints:
    """Test SourceMerger._deduplicate_endpoints method."""

    def test_deduplicate_endpoints_same_method_and_path(self):
        """Test that endpoints with same method+path get deduplicated."""
        merger = SourceMerger()

        endpoints = [
            SourcedEndpoint(
                method="GET",
                path="/api/users",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
            SourcedEndpoint(
                method="GET",
                path="/api/users",
                source=SourceType.GITHUB_REPO,
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]

        deduped = merger._deduplicate_endpoints(endpoints)

        assert len(deduped) == 1
        # Should be from higher-weight source (OPENAPI)
        assert deduped[0].source == SourceType.OPENAPI_SPEC
        # Should be HIGH because from 2+ sources
        assert deduped[0].confidence == ConfidenceLevel.HIGH

    def test_deduplicate_different_methods_not_deduplicated(self):
        """Test that different HTTP methods on same path are NOT deduplicated."""
        merger = SourceMerger()

        endpoints = [
            SourcedEndpoint(
                method="GET",
                path="/api/resource",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
            SourcedEndpoint(
                method="POST",
                path="/api/resource",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
        ]

        deduped = merger._deduplicate_endpoints(endpoints)

        assert len(deduped) == 2

    def test_deduplicate_endpoints_empty_list(self):
        """Test that empty endpoint list returns empty."""
        merger = SourceMerger()
        deduped = merger._deduplicate_endpoints([])
        assert deduped == []

    def test_deduplicate_prefers_more_complete_endpoint(self):
        """Test that deduplication keeps the most complete endpoint."""
        merger = SourceMerger()

        endpoints = [
            SourcedEndpoint(
                method="GET",
                path="/api/users",
                source=SourceType.GITHUB_REPO,
                confidence=ConfidenceLevel.MEDIUM,
            ),
            SourcedEndpoint(
                method="GET",
                path="/api/users",
                summary="List all users",
                parameters=[{"name": "limit", "type": "integer"}],
                response_schema={"type": "array"},
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
        ]

        deduped = merger._deduplicate_endpoints(endpoints)

        assert len(deduped) == 1
        assert deduped[0].summary == "List all users"
        assert deduped[0].parameters is not None

    def test_deduplicate_endpoints_sorted_by_path(self):
        """Test that endpoints are sorted alphabetically by path."""
        merger = SourceMerger()

        endpoints = [
            SourcedEndpoint(
                method="GET",
                path="/z/endpoint",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
            SourcedEndpoint(
                method="GET",
                path="/a/endpoint",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
            SourcedEndpoint(
                method="GET",
                path="/m/endpoint",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
        ]

        deduped = merger._deduplicate_endpoints(endpoints)

        assert deduped[0].path == "/a/endpoint"
        assert deduped[1].path == "/m/endpoint"
        assert deduped[2].path == "/z/endpoint"


class TestComputeOverallConfidence:
    """Test SourceMerger._compute_overall_confidence method."""

    def test_openapi_spec_source_gives_high_confidence(self):
        """Test that OPENAPI_SPEC source results in HIGH confidence."""
        merger = SourceMerger()

        results = [
            SourceResult(
                source_type=SourceType.OPENAPI_SPEC,
                success=True,
            )
        ]

        confidence = merger._compute_overall_confidence(results)
        assert confidence == ConfidenceLevel.HIGH

    def test_github_repo_source_gives_high_confidence(self):
        """Test that GITHUB_REPO source results in HIGH confidence."""
        merger = SourceMerger()

        results = [
            SourceResult(
                source_type=SourceType.GITHUB_REPO,
                success=True,
            )
        ]

        confidence = merger._compute_overall_confidence(results)
        assert confidence == ConfidenceLevel.HIGH

    def test_two_or_more_sources_gives_medium_confidence(self):
        """Test that 2+ sources give MEDIUM confidence."""
        merger = SourceMerger()

        results = [
            SourceResult(
                source_type=SourceType.LLM_KNOWLEDGE,
                success=True,
            ),
            SourceResult(
                source_type=SourceType.WEB_SCRAPE,
                success=True,
            ),
        ]

        confidence = merger._compute_overall_confidence(results)
        assert confidence == ConfidenceLevel.MEDIUM

    def test_single_low_authority_source_gives_low_confidence(self):
        """Test that single low-authority source gives LOW confidence."""
        merger = SourceMerger()

        results = [
            SourceResult(
                source_type=SourceType.LLM_KNOWLEDGE,
                success=True,
            )
        ]

        confidence = merger._compute_overall_confidence(results)
        assert confidence == ConfidenceLevel.LOW

    def test_empty_list_gives_low_confidence(self):
        """Test that empty result list gives LOW confidence."""
        merger = SourceMerger()

        confidence = merger._compute_overall_confidence([])
        assert confidence == ConfidenceLevel.LOW


class TestMerge:
    """Test SourceMerger.merge method (integration test)."""

    def test_merge_multiple_source_results(self):
        """Test merging multiple SourceResult objects."""
        merger = SourceMerger()

        result1 = SourceResult(
            source_type=SourceType.OPENAPI_SPEC,
            success=True,
            product_name="api",
            product_url="https://api.example.com",
            description="Example API",
            capabilities=[
                SourcedFact(
                    value="user management",
                    source=SourceType.OPENAPI_SPEC,
                    confidence=ConfidenceLevel.HIGH,
                )
            ],
            api_endpoints=[
                SourcedEndpoint(
                    method="GET",
                    path="/users",
                    source=SourceType.OPENAPI_SPEC,
                    confidence=ConfidenceLevel.HIGH,
                )
            ],
        )

        result2 = SourceResult(
            source_type=SourceType.GITHUB_REPO,
            success=True,
            product_name="api",
            product_url="https://github.com/user/api",
            description="GitHub version",
            capabilities=[
                SourcedFact(
                    value="user management",
                    source=SourceType.GITHUB_REPO,
                    confidence=ConfidenceLevel.MEDIUM,
                )
            ],
            technical_stack=[
                SourcedFact(
                    value="Python",
                    source=SourceType.GITHUB_REPO,
                    confidence=ConfidenceLevel.HIGH,
                )
            ],
        )

        merged = merger.merge([result1, result2], "api")

        assert merged.product_name == "api"
        assert len(merged.sources_used) == 2
        assert SourceType.OPENAPI_SPEC in merged.sources_used
        assert SourceType.GITHUB_REPO in merged.sources_used

        # Duplicate capability should be deduplicated with HIGH confidence
        assert len(merged.capabilities) == 1
        assert merged.capabilities[0].confidence == ConfidenceLevel.HIGH

        # Endpoint from OPENAPI
        assert len(merged.api_endpoints) == 1

        # Tech stack from GitHub
        assert len(merged.technical_stack) == 1
        assert merged.technical_stack[0].value == "Python"

    def test_merge_handles_failed_sources(self):
        """Test that merge correctly tracks failed sources."""
        merger = SourceMerger()

        result1 = SourceResult(
            source_type=SourceType.OPENAPI_SPEC,
            success=True,
            product_name="api",
        )

        result2 = SourceResult(
            source_type=SourceType.GITHUB_REPO,
            success=False,
            error="Repository not found",
        )

        merged = merger.merge([result1, result2], "api")

        assert len(merged.sources_used) == 1
        assert SourceType.OPENAPI_SPEC in merged.sources_used
        assert len(merged.sources_failed) == 1
        assert merged.sources_failed[0]["source"] == "github_repo"
        assert merged.sources_failed[0]["error"] == "Repository not found"

    def test_merge_computes_overall_confidence(self):
        """Test that merge computes overall confidence correctly."""
        merger = SourceMerger()

        result1 = SourceResult(
            source_type=SourceType.OPENAPI_SPEC,
            success=True,
        )

        merged = merger.merge([result1], "test")

        assert merged.overall_confidence == ConfidenceLevel.HIGH

    def test_merge_builds_combined_content(self):
        """Test that merge builds combined content from raw_content."""
        merger = SourceMerger()

        result1 = SourceResult(
            source_type=SourceType.OPENAPI_SPEC,
            success=True,
            raw_content="# OpenAPI Spec\n\nPaths: ...",
        )

        result2 = SourceResult(
            source_type=SourceType.GITHUB_REPO,
            success=True,
            raw_content="# GitHub README\n\nThis is a project...",
        )

        merged = merger.merge([result1, result2], "test")

        # Should contain both sources' content
        assert "openapi_spec" in merged.combined_content.lower()
        assert "github_repo" in merged.combined_content.lower()
