"""
Data models for the multi-source discovery pipeline.
Every piece of discovered data carries its provenance (source, confidence, evidence).
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class SourceType(str, Enum):
    OPENAPI_SPEC = "openapi_spec"
    PACKAGE_REGISTRY = "package_registry"
    GITHUB_REPO = "github_repo"
    LLM_KNOWLEDGE = "llm_knowledge"
    WEB_SCRAPE = "web_scrape"
    LOCAL_REPO = "local_repo"


class ConfidenceLevel(str, Enum):
    HIGH = "high"       # Directly from authoritative source (OpenAPI spec, package.json)
    MEDIUM = "medium"   # Inferred from structured data (README, GitHub file tree)
    LOW = "low"         # From marketing page or LLM inference


class SourcedFact(BaseModel):
    """A single fact with its provenance."""
    value: str
    source: SourceType
    source_url: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    raw_evidence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "source": self.source.value,
            "source_url": self.source_url,
            "confidence": self.confidence.value,
            "raw_evidence": self.raw_evidence,
        }


class SourcedEndpoint(BaseModel):
    """An API endpoint with provenance."""
    method: Optional[str] = None
    path: str
    summary: Optional[str] = None
    parameters: Optional[List[Dict[str, Any]]] = None
    response_schema: Optional[Dict[str, Any]] = None
    auth_required: Optional[bool] = None
    source: SourceType
    source_url: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "method": self.method,
            "path": self.path,
            "source": self.source.value,
            "confidence": self.confidence.value,
        }
        if self.summary:
            d["summary"] = self.summary
        if self.parameters:
            d["parameters"] = self.parameters
        if self.response_schema:
            d["response_schema"] = self.response_schema
        if self.auth_required is not None:
            d["auth_required"] = self.auth_required
        if self.source_url:
            d["source_url"] = self.source_url
        return d


class SourceResult(BaseModel):
    """Output from a single discovery source."""
    source_type: SourceType
    success: bool
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    # Product identity
    product_name: Optional[str] = None
    product_url: Optional[str] = None
    description: Optional[str] = None

    # Technical data
    capabilities: List[SourcedFact] = Field(default_factory=list)
    api_endpoints: List[SourcedEndpoint] = Field(default_factory=list)
    openapi_spec: Optional[Dict[str, Any]] = None
    auth_methods: List[SourcedFact] = Field(default_factory=list)

    # Ecosystem data
    sdk_languages: List[SourcedFact] = Field(default_factory=list)
    dependencies: List[SourcedFact] = Field(default_factory=list)
    integrations: List[SourcedFact] = Field(default_factory=list)
    technical_stack: List[SourcedFact] = Field(default_factory=list)

    # Architecture
    architecture_patterns: List[SourcedFact] = Field(default_factory=list)
    deployment_options: List[SourcedFact] = Field(default_factory=list)

    # Discovered URLs for other sources to use
    discovered_urls: Dict[str, str] = Field(default_factory=dict)

    # Raw content for downstream analysis
    raw_content: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MergedDiscoveryResult(BaseModel):
    """Output from merging all source results."""
    product_name: str
    product_url: Optional[str] = None
    sources_used: List[SourceType] = Field(default_factory=list)
    sources_failed: List[Dict[str, str]] = Field(default_factory=list)

    # Merged data (each item tracks its source)
    capabilities: List[SourcedFact] = Field(default_factory=list)
    api_endpoints: List[SourcedEndpoint] = Field(default_factory=list)
    openapi_spec: Optional[Dict[str, Any]] = None
    auth_methods: List[SourcedFact] = Field(default_factory=list)
    sdk_languages: List[SourcedFact] = Field(default_factory=list)
    dependencies: List[SourcedFact] = Field(default_factory=list)
    integrations: List[SourcedFact] = Field(default_factory=list)
    technical_stack: List[SourcedFact] = Field(default_factory=list)
    architecture_patterns: List[SourcedFact] = Field(default_factory=list)
    deployment_options: List[SourcedFact] = Field(default_factory=list)
    description: Optional[str] = None

    # Combined raw content for analysis strategy
    combined_content: str = ""

    # Source quality metadata
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    source_coverage: Dict[str, bool] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
