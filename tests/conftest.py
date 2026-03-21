"""
Pytest fixtures for common test data and setup.
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


@pytest.fixture
def sample_sourced_fact():
    """Provide a sample SourcedFact."""
    return SourcedFact(
        value="REST API with JSON responses",
        source=SourceType.OPENAPI_SPEC,
        source_url="https://api.example.com/openapi.json",
        confidence=ConfidenceLevel.HIGH,
        raw_evidence="OpenAPI spec paths object contains 5 endpoints",
    )


@pytest.fixture
def sample_sourced_endpoint():
    """Provide a sample SourcedEndpoint."""
    return SourcedEndpoint(
        method="GET",
        path="/api/v1/users/{id}",
        summary="Retrieve a user by ID",
        parameters=[
            {"name": "id", "in": "path", "required": True, "type": "string"}
        ],
        response_schema={"type": "object", "properties": {"id": {"type": "string"}}},
        auth_required=True,
        source=SourceType.OPENAPI_SPEC,
        source_url="https://api.example.com/openapi.json",
        confidence=ConfidenceLevel.HIGH,
    )


@pytest.fixture
def sample_source_result():
    """Provide a sample SourceResult from a single discovery source."""
    return SourceResult(
        source_type=SourceType.GITHUB_REPO,
        success=True,
        product_name="example-api",
        product_url="https://github.com/user/example-api",
        description="Example API library",
        timestamp=datetime.now(),
        capabilities=[
            SourcedFact(
                value="HTTP request handling",
                source=SourceType.GITHUB_REPO,
                confidence=ConfidenceLevel.MEDIUM,
            )
        ],
        api_endpoints=[
            SourcedEndpoint(
                method="POST",
                path="/api/v1/request",
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
        sdk_languages=[
            SourcedFact(
                value="Python",
                source=SourceType.GITHUB_REPO,
                confidence=ConfidenceLevel.HIGH,
            )
        ],
        discovered_urls={
            "github_repo": "https://github.com/user/example-api",
            "docs": "https://github.com/user/example-api/tree/main/docs",
        },
        raw_content="# Example API\n\nA Python library for HTTP requests.",
    )


@pytest.fixture
def sample_merged_discovery_result():
    """Provide a sample MergedDiscoveryResult from merging multiple sources."""
    return MergedDiscoveryResult(
        product_name="stripe",
        product_url="https://stripe.com",
        sources_used=[SourceType.OPENAPI_SPEC, SourceType.GITHUB_REPO],
        sources_failed=[],
        capabilities=[
            SourcedFact(
                value="Payment processing",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
            SourcedFact(
                value="Subscription management",
                source=SourceType.GITHUB_REPO,
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ],
        api_endpoints=[
            SourcedEndpoint(
                method="POST",
                path="/v1/charges",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
            SourcedEndpoint(
                method="GET",
                path="/v1/customers",
                source=SourceType.OPENAPI_SPEC,
                confidence=ConfidenceLevel.HIGH,
            ),
        ],
        description="Payment processing platform",
        overall_confidence=ConfidenceLevel.HIGH,
        source_coverage={
            "openapi_spec": True,
            "github_repo": True,
            "package_registry": False,
            "llm_knowledge": False,
            "web_scrape": False,
        },
    )


@pytest.fixture
def step1_output_sample():
    """Provide sample Step 1 analysis output."""
    return {
        "summary": "REST API for payment processing",
        "capabilities": [
            "Process credit card payments",
            "Manage customer accounts",
            "Handle refunds",
        ],
        "use_cases": [
            "E-commerce checkout",
            "Subscription billing",
        ],
        "technical_stack": [
            "Python",
            "PostgreSQL",
            "Redis",
        ],
        "integrations": [
            "Shopify",
            "WordPress WooCommerce",
        ],
        "api_endpoints": [
            "POST /v1/charges",
            "GET /v1/customers/{id}",
        ],
        "pricing": {
            "model": "usage-based",
            "tiers": ["Basic", "Pro"],
            "free_tier": True,
            "notes": "2.9% + $0.30 per transaction",
        },
        "target_audience": "Online merchants and SaaS companies",
        "category": "Payment Processing",
        "deployment": "SaaS",
        "underlying_algorithm": {
            "problem_type": "Transaction processing",
            "complexity": "O(1) per transaction",
            "pattern": "Stateless transformer",
        },
        "evidence_tracking": {
            "technical_facts": [
                "API uses REST with JSON responses",
                "Supports OAuth 2.0 authentication",
            ],
            "information_gaps": [
                "Database implementation details",
            ],
            "confidence_level": "High",
        },
    }
