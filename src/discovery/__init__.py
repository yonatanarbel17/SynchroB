"""
Multi-source discovery pipeline for SynchroB.

Discovers product technical information from multiple authoritative sources:
- Package registries (PyPI, NPM)
- OpenAPI/Swagger specifications
- GitHub repositories
- LLM knowledge bases

Each source provides provenance-tracked facts that are merged into a unified result.
"""

from .models import (
    SourceType,
    ConfidenceLevel,
    SourcedFact,
    SourcedEndpoint,
    SourceResult,
    MergedDiscoveryResult,
)
from .orchestrator import DiscoveryOrchestrator
from .merger import SourceMerger
from .local_repo_discovery import LocalRepoDiscovery

__all__ = [
    "SourceType",
    "ConfidenceLevel",
    "SourcedFact",
    "SourcedEndpoint",
    "SourceResult",
    "MergedDiscoveryResult",
    "DiscoveryOrchestrator",
    "SourceMerger",
    "LocalRepoDiscovery",
]
