"""
Integration test for the full local repo discovery pipeline.

Uses SynchroB itself as the test repo and a mocked LLM response
to verify the complete flow: extract → format → (mock) LLM → parse → SourceResult.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.discovery.local_repo_discovery import LocalRepoDiscovery
from src.discovery.models import SourceType, ConfidenceLevel


# The actual SynchroB repo root
REPO_ROOT = str(Path(__file__).resolve().parent.parent)


# Realistic LLM response for SynchroB
SYNCHROB_LLM_RESPONSE = json.dumps({
    "summary": "SynchroB is a multi-source discovery and analysis pipeline that extracts technical DNA from B2B software products. It queries LLM knowledge bases, package registries, GitHub repos, OpenAPI specs, and web pages, then merges provenance-tracked facts through a two-step processor (Step 1: extraction, Step 2: generalization).",
    "capabilities": [
        "Multi-source product discovery via LLM, package registries, GitHub API, OpenAPI probing, and web scraping (src/discovery/orchestrator.py)",
        "Phased concurrent execution with ThreadPoolExecutor for independent discovery sources (src/discovery/orchestrator.py)",
        "Source merging with deduplication and confidence-weighted fact resolution (src/discovery/merger.py)",
        "Step 1 product analysis with pluggable strategies (Direct, Gemini, OpenAI) (src/step1/processor.py)",
        "Step 2 generalization producing Functional DNA, Market Reach, and Friction Report (src/step2/generalizer.py)",
        "Local repository clone and LLM-based source code analysis (src/discovery/local_repo_discovery.py)",
        "Batch analysis of multiple GitHub repos from a URL file (batch_analyze.py)",
    ],
    "category": "Developer Tools / B2B Integration Analysis Platform",
    "technical_stack": [
        "Python (pyproject.toml)",
        "Pydantic (requirements.txt)",
        "google-genai / Gemini API (src/analysis/gemini_client.py)",
        "OpenAI API (src/analysis/openai_client.py)",
        "Firecrawl (src/ingestion/firecrawl_client.py)",
        "tenacity for retry logic (requirements.txt)",
        "requests (requirements.txt)",
    ],
    "api_endpoints": [],
    "sdk_languages": ["Python"],
    "auth_methods": ["API Key (Gemini, OpenAI, Firecrawl, GitHub token)"],
    "integrations": [
        "Google Gemini API",
        "OpenAI API",
        "Firecrawl web scraping API",
        "GitHub REST API",
        "PyPI / NPM package registries",
    ],
    "architecture": {
        "pattern": "monolith",
        "entry_points": ["batch_analyze.py", "src/step1/processor.py", "src/step2/generalizer.py"],
        "data_flow": "Discovery sources → SourceResult → Merger → MergedDiscoveryResult → Step1 Processor → Step2 Generalizer",
        "persistence": "File-based JSON cache (src/cache.py)",
        "concurrency_model": "Multi-threaded via ThreadPoolExecutor in discovery orchestrator",
    },
    "algorithms": {
        "problem_type": "Information extraction and classification pipeline",
        "core_patterns": ["Strategy pattern", "Pipeline pattern", "Source merger with weighted deduplication"],
        "complexity_indicators": "Linear in number of sources and facts; LLM calls dominate runtime",
        "evidence": "src/step1/analysis_strategy.py, src/discovery/merger.py",
    },
    "dependencies": {
        "runtime": ["pydantic", "google-genai", "openai", "requests", "tenacity", "python-dotenv", "firecrawl-py"],
        "dev": ["pytest", "black", "ruff"],
        "infrastructure": [],
    },
    "deployment": {
        "containerized": False,
        "ci_cd": "GitHub Actions (.github/workflows/ci.yml)",
        "environment_config": "Environment variables via .env file (config.py)",
    },
    "code_quality_signals": {
        "has_tests": True,
        "test_framework": "pytest",
        "has_linting": True,
        "has_type_hints": True,
        "documentation_quality": "well-documented",
    },
    "evidence_tracking": {
        "files_analyzed": [
            "src/discovery/orchestrator.py",
            "src/discovery/merger.py",
            "src/discovery/models.py",
            "src/step1/processor.py",
            "src/step2/generalizer.py",
            "src/utils.py",
            "config.py",
            "batch_analyze.py",
            "requirements.txt",
            "pyproject.toml",
        ],
        "confidence_level": "High",
        "information_gaps": ["No OpenAPI spec on disk", "Step 3 matching not yet implemented"],
    },
})


class TestIntegrationLocalRepo:
    """End-to-end test using SynchroB's own repo with a mocked LLM."""

    def test_extract_and_analyze_synchrob(self):
        """
        Run the full pipeline on SynchroB itself:
        1. Extract using real script (subprocess)
        2. Format for LLM
        3. Mock the LLM response
        4. Parse into SourceResult
        """
        gemini_mock = MagicMock()
        discovery = LocalRepoDiscovery(gemini_client=gemini_mock)

        # Run real extraction
        extraction = discovery._run_extraction(REPO_ROOT)
        assert extraction is not None
        assert extraction["total_files"] > 20
        assert ".py" in extraction["language_distribution"]

        # Format for LLM — verify it produces something reasonable
        formatted = discovery._format_extraction_for_llm(extraction)
        assert len(formatted) > 1000
        assert "requirements.txt" in formatted or "pyproject.toml" in formatted
        assert "Source Code Samples" in formatted

        # Build SourceResult from mocked LLM response
        data = json.loads(SYNCHROB_LLM_RESPONSE)
        result = discovery._build_source_result(
            data,
            "https://github.com/yonatanarbel17/SynchroB.git",
            extraction,
        )

        # Verify the result
        assert result.success
        assert result.source_type == SourceType.LOCAL_REPO
        assert result.product_name == "SynchroB"
        assert len(result.capabilities) >= 5
        assert all(c.confidence == ConfidenceLevel.HIGH for c in result.capabilities)
        assert len(result.technical_stack) >= 3
        assert any("Pydantic" in t.value for t in result.technical_stack)
        assert any("monolith" in a.value for a in result.architecture_patterns)
        assert len(result.integrations) >= 3

    def test_extraction_script_handles_synchrob(self):
        """Verify the extraction script can handle the SynchroB repo correctly."""
        gemini_mock = MagicMock()
        discovery = LocalRepoDiscovery(gemini_client=gemini_mock)

        extraction = discovery._run_extraction(REPO_ROOT)

        # Structural checks
        assert "file_tree" in extraction
        assert "source_samples" in extraction
        assert "dependencies" in extraction
        assert "readme" in extraction

        # Should find Python files
        py_count = extraction["language_distribution"].get(".py", 0)
        assert py_count > 10

        # Should find dependency manifests
        dep_files = list(extraction["dependencies"].keys())
        assert any("requirements" in f for f in dep_files) or any("pyproject" in f for f in dep_files)

        # Source samples should include key files
        sample_files = list(extraction["source_samples"].keys())
        assert len(sample_files) > 5

    def test_batch_analyze_source_result_conversion(self):
        """Verify that SourceResult → Step 1 dict conversion preserves data."""
        from batch_analyze import _source_result_to_step1_dict

        gemini_mock = MagicMock()
        discovery = LocalRepoDiscovery(gemini_client=gemini_mock)

        extraction = discovery._run_extraction(REPO_ROOT)
        data = json.loads(SYNCHROB_LLM_RESPONSE)
        result = discovery._build_source_result(
            data,
            "https://github.com/yonatanarbel17/SynchroB.git",
            extraction,
        )

        step1_dict = _source_result_to_step1_dict(result)

        # Verify Step 1 dict has the right shape for Step 2
        assert step1_dict["product_name"] == "SynchroB"
        assert len(step1_dict["capabilities"]) >= 5
        assert len(step1_dict["technical_stack"]) >= 3
        assert step1_dict["source"] == "local_repo"
        assert step1_dict["source_confidence"] == "high"
        assert "summary" in step1_dict
        assert isinstance(step1_dict["api_endpoints"], list)
