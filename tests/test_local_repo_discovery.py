"""
Tests for LocalRepoDiscovery — the local repo clone + LLM analysis source.
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from src.discovery.local_repo_discovery import LocalRepoDiscovery, EXTRACTION_SCRIPT, SKILL_PATH
from src.discovery.models import SourceType, ConfidenceLevel, SourceResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_EXTRACTION = {
    "repo_path": "/tmp/test_repo",
    "repo_name": "test-project",
    "total_files": 15,
    "file_tree": [
        "README.md",
        "requirements.txt",
        "main.py",
        "src/app.py",
        "src/routes.py",
        "src/models.py",
        "tests/test_app.py",
    ],
    "language_distribution": {".py": 5},
    "readme": "# Test Project\nA REST API for managing widgets.",
    "dependencies": {
        "requirements.txt": {
            "file": "requirements.txt",
            "ecosystem": "pip",
            "raw": "flask==2.3.0\nsqlalchemy==2.0.0\nredis==5.0.0\n",
            "parsed": {"packages": ["flask==2.3.0", "sqlalchemy==2.0.0", "redis==5.0.0"]},
        }
    },
    "openapi_specs": {},
    "config_files": {
        "Dockerfile": "FROM python:3.11-slim\nCOPY . /app\nCMD [\"python\", \"main.py\"]"
    },
    "source_samples": {
        "main.py": "from flask import Flask\napp = Flask(__name__)\n",
        "src/routes.py": "@app.route('/widgets', methods=['GET'])\ndef get_widgets():\n    return jsonify(widgets)\n",
    },
}

SAMPLE_LLM_RESPONSE = json.dumps({
    "summary": "A Flask REST API for managing widgets with SQLAlchemy ORM and Redis caching.",
    "capabilities": [
        "CRUD operations on widgets (src/routes.py)",
        "Redis caching layer for frequently accessed widgets (src/cache.py)",
    ],
    "category": "REST API",
    "technical_stack": [
        "Flask (requirements.txt)",
        "SQLAlchemy (requirements.txt)",
        "Redis (requirements.txt)",
    ],
    "api_endpoints": [
        "GET /widgets — List all widgets (src/routes.py:1)",
        "POST /widgets — Create a widget (src/routes.py:10)",
    ],
    "sdk_languages": [],
    "auth_methods": ["API Key"],
    "integrations": ["Redis"],
    "architecture": {
        "pattern": "monolith",
        "entry_points": ["main.py"],
        "data_flow": "HTTP request → Flask route → SQLAlchemy → PostgreSQL",
        "persistence": "SQLAlchemy ORM with PostgreSQL",
        "concurrency_model": "sync (Flask/WSGI)",
    },
    "algorithms": {
        "problem_type": "CRUD operations",
        "core_patterns": ["Repository pattern"],
        "complexity_indicators": "O(1) lookups via Redis cache",
        "evidence": "src/routes.py, src/cache.py",
    },
    "dependencies": {
        "runtime": ["flask", "sqlalchemy", "redis"],
        "dev": ["pytest"],
        "infrastructure": ["PostgreSQL", "Redis"],
    },
    "deployment": {
        "containerized": True,
        "ci_cd": "none observed",
        "environment_config": "Environment variables",
    },
    "code_quality_signals": {
        "has_tests": True,
        "test_framework": "pytest",
        "has_linting": False,
        "has_type_hints": False,
        "documentation_quality": "sparse",
    },
    "evidence_tracking": {
        "files_analyzed": ["main.py", "src/routes.py", "requirements.txt", "Dockerfile"],
        "confidence_level": "High",
        "information_gaps": ["No OpenAPI spec found"],
    },
})


@pytest.fixture
def discovery():
    """Create a LocalRepoDiscovery with mocked clients."""
    gemini = MagicMock()
    return LocalRepoDiscovery(gemini_client=gemini)


# ---------------------------------------------------------------------------
# Tests: _load_skill
# ---------------------------------------------------------------------------

class TestLoadSkill:
    def test_loads_skill_from_disk(self, discovery):
        """Should load and cache skill instructions from SKILL.md."""
        if SKILL_PATH.exists():
            instructions = discovery._load_skill()
            assert len(instructions) > 100
            assert "Repo Analyzer" in instructions or "technical analysis" in instructions.lower()
            # Verify caching
            assert discovery._skill_instructions is not None
            instructions2 = discovery._load_skill()
            assert instructions2 is instructions  # Same object = cached

    def test_fallback_when_skill_missing(self, discovery):
        """Should return a minimal prompt when SKILL.md is missing."""
        with patch.object(Path, "exists", return_value=False):
            instructions = discovery._load_skill()
            assert "analyze" in instructions.lower() or "JSON" in instructions


# ---------------------------------------------------------------------------
# Tests: _format_extraction_for_llm
# ---------------------------------------------------------------------------

class TestFormatExtraction:
    def test_includes_file_tree(self):
        text = LocalRepoDiscovery._format_extraction_for_llm(SAMPLE_EXTRACTION)
        assert "File Tree" in text
        assert "main.py" in text
        assert "src/routes.py" in text

    def test_includes_readme(self):
        text = LocalRepoDiscovery._format_extraction_for_llm(SAMPLE_EXTRACTION)
        assert "README" in text
        assert "Test Project" in text

    def test_includes_dependencies(self):
        text = LocalRepoDiscovery._format_extraction_for_llm(SAMPLE_EXTRACTION)
        assert "Dependency Manifests" in text
        assert "flask" in text

    def test_includes_source_samples(self):
        text = LocalRepoDiscovery._format_extraction_for_llm(SAMPLE_EXTRACTION)
        assert "Source Code Samples" in text
        assert "get_widgets" in text

    def test_includes_config_files(self):
        text = LocalRepoDiscovery._format_extraction_for_llm(SAMPLE_EXTRACTION)
        assert "Configuration Files" in text
        assert "Dockerfile" in text

    def test_truncates_large_file_tree(self):
        big_extraction = {**SAMPLE_EXTRACTION, "file_tree": [f"file_{i}.py" for i in range(500)]}
        text = LocalRepoDiscovery._format_extraction_for_llm(big_extraction)
        assert "and 300 more files" in text

    def test_handles_empty_extraction(self):
        empty = {"file_tree": [], "total_files": 0}
        text = LocalRepoDiscovery._format_extraction_for_llm(empty)
        assert "File Tree (0 files)" in text


# ---------------------------------------------------------------------------
# Tests: _build_source_result
# ---------------------------------------------------------------------------

class TestBuildSourceResult:
    def test_builds_successful_result(self, discovery):
        data = json.loads(SAMPLE_LLM_RESPONSE)
        result = discovery._build_source_result(data, "https://github.com/user/test-project.git", SAMPLE_EXTRACTION)

        assert result.success
        assert result.source_type == SourceType.LOCAL_REPO
        assert result.product_name == "test-project"

    def test_capabilities_are_high_confidence(self, discovery):
        data = json.loads(SAMPLE_LLM_RESPONSE)
        result = discovery._build_source_result(data, "https://github.com/u/r.git", SAMPLE_EXTRACTION)

        assert len(result.capabilities) == 2
        for cap in result.capabilities:
            assert cap.confidence == ConfidenceLevel.HIGH
            assert cap.source == SourceType.LOCAL_REPO

    def test_api_endpoints_parsed(self, discovery):
        data = json.loads(SAMPLE_LLM_RESPONSE)
        result = discovery._build_source_result(data, "https://github.com/u/r.git", SAMPLE_EXTRACTION)

        assert len(result.api_endpoints) == 2
        methods = {ep.method for ep in result.api_endpoints}
        assert "GET" in methods
        assert "POST" in methods

    def test_technical_stack_extracted(self, discovery):
        data = json.loads(SAMPLE_LLM_RESPONSE)
        result = discovery._build_source_result(data, "https://github.com/u/r.git", SAMPLE_EXTRACTION)

        stack_values = {f.value for f in result.technical_stack}
        assert "Flask (requirements.txt)" in stack_values
        assert "SQLAlchemy (requirements.txt)" in stack_values

    def test_architecture_patterns(self, discovery):
        data = json.loads(SAMPLE_LLM_RESPONSE)
        result = discovery._build_source_result(data, "https://github.com/u/r.git", SAMPLE_EXTRACTION)

        arch_values = [f.value for f in result.architecture_patterns]
        assert any("monolith" in v for v in arch_values)

    def test_deployment_info(self, discovery):
        data = json.loads(SAMPLE_LLM_RESPONSE)
        result = discovery._build_source_result(data, "https://github.com/u/r.git", SAMPLE_EXTRACTION)

        deploy_values = [f.value for f in result.deployment_options]
        assert any("Docker" in v for v in deploy_values)

    def test_dependencies_extracted(self, discovery):
        data = json.loads(SAMPLE_LLM_RESPONSE)
        result = discovery._build_source_result(data, "https://github.com/u/r.git", SAMPLE_EXTRACTION)

        dep_values = {f.value for f in result.dependencies}
        assert "flask" in dep_values
        assert any("PostgreSQL" in v for v in dep_values)

    def test_discovered_urls_set(self, discovery):
        data = json.loads(SAMPLE_LLM_RESPONSE)
        result = discovery._build_source_result(data, "https://github.com/u/r.git", SAMPLE_EXTRACTION)

        assert result.discovered_urls.get("github_repo") == "https://github.com/u/r.git"

    def test_raw_content_built(self, discovery):
        data = json.loads(SAMPLE_LLM_RESPONSE)
        result = discovery._build_source_result(data, "https://github.com/u/r.git", SAMPLE_EXTRACTION)

        assert result.raw_content is not None
        assert "Capabilities" in result.raw_content


# ---------------------------------------------------------------------------
# Tests: discover (integration-style with mocks)
# ---------------------------------------------------------------------------

class TestDiscover:
    @patch.object(LocalRepoDiscovery, "_clone_repo")
    @patch.object(LocalRepoDiscovery, "_run_extraction")
    @patch.object(LocalRepoDiscovery, "_query_llm")
    def test_full_pipeline(self, mock_query, mock_extract, mock_clone, discovery):
        """Full pipeline: clone → extract → LLM → SourceResult"""
        mock_clone.return_value = ("/tmp/test-project", "/tmp/synchrob_local_xxx")
        mock_extract.return_value = SAMPLE_EXTRACTION
        mock_query.return_value = SAMPLE_LLM_RESPONSE

        result = discovery.discover("https://github.com/user/test-project.git")

        assert result.success
        assert result.source_type == SourceType.LOCAL_REPO
        assert len(result.capabilities) > 0
        mock_clone.assert_called_once()
        mock_extract.assert_called_once()
        mock_query.assert_called_once()

    @patch.object(LocalRepoDiscovery, "_clone_repo")
    @patch.object(LocalRepoDiscovery, "_run_extraction")
    def test_extraction_failure(self, mock_extract, mock_clone, discovery):
        """Should return failure SourceResult when extraction fails."""
        mock_clone.return_value = ("/tmp/test-project", "/tmp/synchrob_local_xxx")
        mock_extract.return_value = None

        result = discovery.discover("https://github.com/user/test-project.git")

        assert not result.success
        assert "Extraction" in result.error

    @patch.object(LocalRepoDiscovery, "_clone_repo")
    @patch.object(LocalRepoDiscovery, "_run_extraction")
    @patch.object(LocalRepoDiscovery, "_query_llm")
    def test_llm_failure(self, mock_query, mock_extract, mock_clone, discovery):
        """Should return failure when LLM returns None."""
        mock_clone.return_value = ("/tmp/test-project", "/tmp/synchrob_local_xxx")
        mock_extract.return_value = SAMPLE_EXTRACTION
        mock_query.return_value = None

        result = discovery.discover("https://github.com/user/test-project.git")

        assert not result.success
        assert "LLM analysis failed" in result.error

    @patch.object(LocalRepoDiscovery, "_clone_repo")
    @patch.object(LocalRepoDiscovery, "_run_extraction")
    @patch.object(LocalRepoDiscovery, "_query_llm")
    def test_invalid_json_from_llm(self, mock_query, mock_extract, mock_clone, discovery):
        """Should handle non-JSON LLM responses gracefully."""
        mock_clone.return_value = ("/tmp/test-project", "/tmp/synchrob_local_xxx")
        mock_extract.return_value = SAMPLE_EXTRACTION
        mock_query.return_value = "This is not JSON at all!"

        result = discovery.discover("https://github.com/user/test-project.git")

        assert not result.success
        assert "JSON parse error" in result.error

    @patch.object(LocalRepoDiscovery, "_run_extraction")
    def test_local_path_skips_clone(self, mock_extract, discovery):
        """Should skip cloning when local_path is provided."""
        mock_extract.return_value = SAMPLE_EXTRACTION

        with patch.object(discovery, "_query_llm", return_value=SAMPLE_LLM_RESPONSE):
            result = discovery.discover(
                "https://github.com/user/test-project.git",
                local_path="/existing/repo",
            )

        assert result.success
        # _clone_repo should NOT have been called
        mock_extract.assert_called_once_with("/existing/repo")

    @patch.object(LocalRepoDiscovery, "_clone_repo")
    @patch.object(LocalRepoDiscovery, "_run_extraction")
    @patch.object(LocalRepoDiscovery, "_query_llm")
    def test_cleanup_on_success(self, mock_query, mock_extract, mock_clone, discovery):
        """Should clean up clone directory after successful analysis."""
        mock_clone.return_value = ("/tmp/test-project", "/tmp/synchrob_local_xxx")
        mock_extract.return_value = SAMPLE_EXTRACTION
        mock_query.return_value = SAMPLE_LLM_RESPONSE

        with patch("shutil.rmtree") as mock_rmtree:
            discovery.discover("https://github.com/user/test-project.git")
            mock_rmtree.assert_called_once_with("/tmp/synchrob_local_xxx", ignore_errors=True)

    @patch.object(LocalRepoDiscovery, "_clone_repo")
    @patch.object(LocalRepoDiscovery, "_run_extraction")
    @patch.object(LocalRepoDiscovery, "_query_llm")
    def test_keep_clone(self, mock_query, mock_extract, mock_clone, discovery):
        """Should NOT clean up when keep_clone=True."""
        mock_clone.return_value = ("/tmp/test-project", "/tmp/synchrob_local_xxx")
        mock_extract.return_value = SAMPLE_EXTRACTION
        mock_query.return_value = SAMPLE_LLM_RESPONSE

        with patch("shutil.rmtree") as mock_rmtree:
            discovery.discover("https://github.com/user/test-project.git", keep_clone=True)
            mock_rmtree.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: batch_analyze helpers
# ---------------------------------------------------------------------------

class TestBatchHelpers:
    def test_parse_url_file(self, tmp_path):
        """Test URL file parsing with comments and blank lines."""
        from batch_analyze import parse_url_file

        url_file = tmp_path / "repos.txt"
        url_file.write_text(
            "# Payment processors\n"
            "https://github.com/stripe/stripe-python.git\n"
            "\n"
            "# Auth\n"
            "https://github.com/jpadilla/pyjwt.git\n"
            "not-a-github-url\n"
        )

        urls = parse_url_file(str(url_file))
        assert len(urls) == 2
        assert "stripe-python" in urls[0]
        assert "pyjwt" in urls[1]

    def test_source_result_to_step1_dict(self):
        """Test conversion of SourceResult to Step 1 dict format."""
        from batch_analyze import _source_result_to_step1_dict
        from src.discovery.models import SourcedFact, SourcedEndpoint

        result = SourceResult(
            source_type=SourceType.LOCAL_REPO,
            success=True,
            product_name="test-project",
            product_url="https://github.com/user/test-project",
            description="A test project",
            capabilities=[
                SourcedFact(value="Widget management", source=SourceType.LOCAL_REPO),
            ],
            api_endpoints=[
                SourcedEndpoint(method="GET", path="/widgets", source=SourceType.LOCAL_REPO),
            ],
            technical_stack=[
                SourcedFact(value="Flask", source=SourceType.LOCAL_REPO),
            ],
        )

        step1 = _source_result_to_step1_dict(result)

        assert step1["product_name"] == "test-project"
        assert step1["summary"] == "A test project"
        assert "Widget management" in step1["capabilities"]
        assert len(step1["api_endpoints"]) == 1
        assert step1["api_endpoints"][0]["method"] == "GET"
        assert "Flask" in step1["technical_stack"]
        assert step1["source"] == "local_repo"
        assert step1["source_confidence"] == "high"
