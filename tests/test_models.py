"""
Tests for src/discovery/models.py
"""

import pytest
from datetime import datetime
from src.discovery.models import (
    SourceType,
    ConfidenceLevel,
    SourcedFact,
    SourcedEndpoint,
    SourceResult,
    MergedDiscoveryResult,
)


class TestSourcedFact:
    """Test SourcedFact model."""

    def test_sourced_fact_creation(self):
        """Test creating a SourcedFact."""
        fact = SourcedFact(
            value="Supports REST API",
            source=SourceType.OPENAPI_SPEC,
            confidence=ConfidenceLevel.HIGH,
        )
        assert fact.value == "Supports REST API"
        assert fact.source == SourceType.OPENAPI_SPEC
        assert fact.confidence == ConfidenceLevel.HIGH

    def test_sourced_fact_with_url_and_evidence(self):
        """Test SourcedFact with optional fields."""
        fact = SourcedFact(
            value="Uses PostgreSQL",
            source=SourceType.GITHUB_REPO,
            source_url="https://github.com/example/repo",
            confidence=ConfidenceLevel.MEDIUM,
            raw_evidence="Found Dockerfile with postgres image",
        )
        assert fact.source_url == "https://github.com/example/repo"
        assert fact.raw_evidence == "Found Dockerfile with postgres image"

    def test_sourced_fact_default_confidence(self):
        """Test that default confidence is MEDIUM."""
        fact = SourcedFact(
            value="test",
            source=SourceType.WEB_SCRAPE,
        )
        assert fact.confidence == ConfidenceLevel.MEDIUM

    def test_sourced_fact_to_dict(self):
        """Test SourcedFact.to_dict() serialization."""
        fact = SourcedFact(
            value="test capability",
            source=SourceType.OPENAPI_SPEC,
            source_url="https://api.example.com/spec.json",
            confidence=ConfidenceLevel.HIGH,
            raw_evidence="From OpenAPI paths",
        )
        d = fact.to_dict()
        assert d["value"] == "test capability"
        assert d["source"] == "openapi_spec"
        assert d["source_url"] == "https://api.example.com/spec.json"
        assert d["confidence"] == "high"
        assert d["raw_evidence"] == "From OpenAPI paths"

    def test_sourced_fact_to_dict_without_optional_fields(self):
        """Test to_dict() with minimal fields."""
        fact = SourcedFact(value="test", source=SourceType.LLM_KNOWLEDGE)
        d = fact.to_dict()
        assert d["value"] == "test"
        assert d["source"] == "llm_knowledge"
        assert d["confidence"] == "medium"
        assert d["source_url"] is None
        assert d["raw_evidence"] is None


class TestSourcedEndpoint:
    """Test SourcedEndpoint model."""

    def test_sourced_endpoint_basic(self):
        """Test creating a basic SourcedEndpoint."""
        ep = SourcedEndpoint(
            method="GET",
            path="/api/v1/users",
            source=SourceType.OPENAPI_SPEC,
        )
        assert ep.method == "GET"
        assert ep.path == "/api/v1/users"
        assert ep.source == SourceType.OPENAPI_SPEC

    def test_sourced_endpoint_with_all_fields(self):
        """Test SourcedEndpoint with all optional fields."""
        ep = SourcedEndpoint(
            method="POST",
            path="/api/v1/payments",
            summary="Create a payment",
            parameters=[
                {"name": "amount", "in": "body", "required": True}
            ],
            response_schema={"type": "object"},
            auth_required=True,
            source=SourceType.OPENAPI_SPEC,
            source_url="https://api.example.com/spec.json",
            confidence=ConfidenceLevel.HIGH,
        )
        assert ep.summary == "Create a payment"
        assert ep.parameters is not None
        assert ep.auth_required is True
        assert ep.response_schema is not None

    def test_sourced_endpoint_default_confidence(self):
        """Test that endpoint default confidence is MEDIUM."""
        ep = SourcedEndpoint(
            path="/api/test",
            source=SourceType.GITHUB_REPO,
        )
        assert ep.confidence == ConfidenceLevel.MEDIUM

    def test_sourced_endpoint_to_dict_minimal(self):
        """Test to_dict() with minimal fields."""
        ep = SourcedEndpoint(
            method="DELETE",
            path="/api/v1/resource/{id}",
            source=SourceType.GITHUB_REPO,
            confidence=ConfidenceLevel.LOW,
        )
        d = ep.to_dict()
        assert d["method"] == "DELETE"
        assert d["path"] == "/api/v1/resource/{id}"
        assert d["source"] == "github_repo"
        assert d["confidence"] == "low"
        assert "summary" not in d

    def test_sourced_endpoint_to_dict_with_optional_fields(self):
        """Test to_dict() includes optional fields when present."""
        ep = SourcedEndpoint(
            method="GET",
            path="/api/v1/data",
            summary="Fetch data",
            parameters=[{"name": "id", "type": "string"}],
            auth_required=False,
            source=SourceType.OPENAPI_SPEC,
        )
        d = ep.to_dict()
        assert "summary" in d
        assert d["summary"] == "Fetch data"
        assert "parameters" in d
        assert "auth_required" in d
        assert d["auth_required"] is False


class TestSourceResult:
    """Test SourceResult model."""

    def test_source_result_creation(self):
        """Test creating a SourceResult."""
        result = SourceResult(
            source_type=SourceType.GITHUB_REPO,
            success=True,
            product_name="example-lib",
        )
        assert result.source_type == SourceType.GITHUB_REPO
        assert result.success is True
        assert result.product_name == "example-lib"
        assert isinstance(result.timestamp, datetime)

    def test_source_result_default_factory_fields(self):
        """Test that default factory fields create empty lists."""
        result = SourceResult(
            source_type=SourceType.WEB_SCRAPE,
            success=False,
            error="Page not found",
        )
        assert result.capabilities == []
        assert result.api_endpoints == []
        assert result.auth_methods == []
        assert result.sdk_languages == []
        assert result.dependencies == []
        assert result.integrations == []
        assert result.technical_stack == []
        assert result.architecture_patterns == []
        assert result.deployment_options == []

    def test_source_result_with_data(self):
        """Test SourceResult populated with data."""
        caps = [SourcedFact(
            value="caching",
            source=SourceType.GITHUB_REPO,
        )]
        endpoints = [SourcedEndpoint(
            method="GET",
            path="/cache",
            source=SourceType.GITHUB_REPO,
        )]
        result = SourceResult(
            source_type=SourceType.GITHUB_REPO,
            success=True,
            product_name="cache-lib",
            capabilities=caps,
            api_endpoints=endpoints,
            discovered_urls={"repo": "https://github.com/user/repo"},
        )
        assert len(result.capabilities) == 1
        assert len(result.api_endpoints) == 1
        assert result.discovered_urls["repo"] == "https://github.com/user/repo"


class TestMergedDiscoveryResult:
    """Test MergedDiscoveryResult model."""

    def test_merged_result_creation(self):
        """Test creating a MergedDiscoveryResult."""
        result = MergedDiscoveryResult(
            product_name="stripe",
            product_url="https://stripe.com",
        )
        assert result.product_name == "stripe"
        assert result.product_url == "https://stripe.com"

    def test_merged_result_default_fields(self):
        """Test that default fields are initialized correctly."""
        result = MergedDiscoveryResult(product_name="test-product")
        assert result.sources_used == []
        assert result.sources_failed == []
        assert result.capabilities == []
        assert result.api_endpoints == []
        assert result.auth_methods == []
        assert result.sdk_languages == []
        assert result.dependencies == []
        assert result.integrations == []
        assert result.technical_stack == []
        assert result.architecture_patterns == []
        assert result.deployment_options == []
        assert result.combined_content == ""
        assert result.overall_confidence == ConfidenceLevel.MEDIUM
        assert result.source_coverage == {}

    def test_merged_result_with_comprehensive_data(self):
        """Test MergedDiscoveryResult with full data."""
        cap = SourcedFact(
            value="payment processing",
            source=SourceType.OPENAPI_SPEC,
            confidence=ConfidenceLevel.HIGH,
        )
        ep = SourcedEndpoint(
            method="POST",
            path="/v1/charges",
            source=SourceType.OPENAPI_SPEC,
            confidence=ConfidenceLevel.HIGH,
        )
        result = MergedDiscoveryResult(
            product_name="stripe",
            product_url="https://stripe.com",
            sources_used=[SourceType.OPENAPI_SPEC, SourceType.GITHUB_REPO],
            sources_failed=[],
            capabilities=[cap],
            api_endpoints=[ep],
            overall_confidence=ConfidenceLevel.HIGH,
            source_coverage={
                "openapi_spec": True,
                "github_repo": True,
                "llm_knowledge": False,
            },
        )
        assert len(result.capabilities) == 1
        assert len(result.api_endpoints) == 1
        assert result.overall_confidence == ConfidenceLevel.HIGH
        assert result.source_coverage["openapi_spec"] is True


class TestEnums:
    """Test enum classes."""

    def test_source_type_values(self):
        """Test SourceType enum values."""
        assert SourceType.OPENAPI_SPEC.value == "openapi_spec"
        assert SourceType.PACKAGE_REGISTRY.value == "package_registry"
        assert SourceType.GITHUB_REPO.value == "github_repo"
        assert SourceType.LLM_KNOWLEDGE.value == "llm_knowledge"
        assert SourceType.WEB_SCRAPE.value == "web_scrape"

    def test_confidence_level_values(self):
        """Test ConfidenceLevel enum values."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"

    def test_enum_string_comparison(self):
        """Test that enum values can be compared as strings."""
        assert SourceType.GITHUB_REPO.value == "github_repo"
        assert ConfidenceLevel.HIGH.value == "high"
