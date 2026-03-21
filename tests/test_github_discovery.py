"""
Tests for src/discovery/github_discovery.py
"""

import pytest
from unittest.mock import MagicMock, patch
from src.discovery.github_discovery import GitHubDiscovery
from src.discovery.models import SourceType


class TestParseRepoUrl:
    """Test GitHubDiscovery._parse_repo_url static method."""

    def test_parse_standard_github_url(self):
        """Test parsing standard GitHub URL."""
        result = GitHubDiscovery._parse_repo_url("https://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_parse_url_with_git_suffix(self):
        """Test parsing URL with .git suffix."""
        result = GitHubDiscovery._parse_repo_url("https://github.com/owner/repo.git")
        assert result == ("owner", "repo")

    def test_parse_url_with_git_plus_prefix(self):
        """Test parsing URL with git+ prefix."""
        result = GitHubDiscovery._parse_repo_url("git+https://github.com/owner/repo.git")
        assert result == ("owner", "repo")

    def test_parse_url_with_git_scheme(self):
        """Test parsing URL with git:// scheme."""
        result = GitHubDiscovery._parse_repo_url("git://github.com/owner/repo.git")
        assert result == ("owner", "repo")

    def test_parse_url_with_trailing_slash(self):
        """Test parsing URL with trailing slash."""
        result = GitHubDiscovery._parse_repo_url("https://github.com/owner/repo/")
        assert result == ("owner", "repo")

    def test_parse_url_with_subpath(self):
        """Test parsing URL with subpath (tree/branch/etc)."""
        result = GitHubDiscovery._parse_repo_url(
            "https://github.com/owner/repo/tree/main/src"
        )
        assert result == ("owner", "repo")

    def test_parse_url_with_all_transformations(self):
        """Test URL with multiple transformations needed."""
        result = GitHubDiscovery._parse_repo_url(
            "git+https://github.com/user/project.git/"
        )
        assert result == ("user", "project")

    def test_parse_invalid_url_returns_none(self):
        """Test that invalid URL returns None."""
        result = GitHubDiscovery._parse_repo_url("https://example.com/not-github")
        assert result is None

    def test_parse_topic_path_returns_none(self):
        """Test that GitHub special paths return None."""
        result = GitHubDiscovery._parse_repo_url("https://github.com/topics/python")
        assert result is None

    def test_parse_explore_path_returns_none(self):
        """Test that explore path returns None."""
        result = GitHubDiscovery._parse_repo_url("https://github.com/explore/trending")
        assert result is None

    def test_parse_settings_path_returns_none(self):
        """Test that settings path returns None."""
        result = GitHubDiscovery._parse_repo_url("https://github.com/settings/profile")
        assert result is None

    def test_parse_with_whitespace(self):
        """Test parsing URL with surrounding whitespace."""
        result = GitHubDiscovery._parse_repo_url("  https://github.com/owner/repo  ")
        assert result == ("owner", "repo")

    def test_parse_http_url(self):
        """Test parsing http:// URL (not https)."""
        result = GitHubDiscovery._parse_repo_url("http://github.com/owner/repo")
        assert result == ("owner", "repo")


class TestAnalyzeFileTree:
    """Test GitHubDiscovery._analyze_file_tree method."""

    def test_detect_nodejs_from_package_json(self):
        """Test detection of Node.js from package.json."""
        discovery = GitHubDiscovery()

        tree = [
            {"path": "package.json", "type": "blob"},
            {"path": "README.md", "type": "blob"},
        ]

        result = discovery._analyze_file_tree(
            tree, "owner", "repo", "https://github.com/owner/repo"
        )

        assert any(
            fact.value == "Node.js"
            for fact in result["technical_stack"]
        )

    def test_detect_openapi_files(self):
        """Test detection of OpenAPI spec files."""
        discovery = GitHubDiscovery()

        tree = [
            {"path": "docs/openapi.json", "type": "blob"},
            {"path": "src/main.py", "type": "blob"},
        ]

        result = discovery._analyze_file_tree(
            tree, "owner", "repo", "https://github.com/owner/repo"
        )

        assert "docs/openapi.json" in result["openapi_files"]
        assert "openapi_spec_raw_url" in result["discovered_urls"]

    def test_infer_primary_language_from_extensions(self):
        """Test inference of primary language from file extensions."""
        discovery = GitHubDiscovery()

        tree = [
            {"path": "src/main.py", "type": "blob"},
            {"path": "src/utils.py", "type": "blob"},
            {"path": "src/helpers.py", "type": "blob"},
            {"path": "src/single.js", "type": "blob"},
        ]

        result = discovery._analyze_file_tree(
            tree, "owner", "repo", "https://github.com/owner/repo"
        )

        # Python appears 3 times, JS appears 1 time
        assert result["primary_language"] == "Python"

    def test_detect_multiple_stack_indicators(self):
        """Test detection of multiple technical stack indicators."""
        discovery = GitHubDiscovery()

        tree = [
            {"path": "package.json", "type": "blob"},
            {"path": "Dockerfile", "type": "blob"},
            {"path": "docker-compose.yml", "type": "blob"},
        ]

        result = discovery._analyze_file_tree(
            tree, "owner", "repo", "https://github.com/owner/repo"
        )

        stack_values = {fact.value for fact in result["technical_stack"]}
        assert "Node.js" in stack_values
        assert "Docker" in stack_values
        assert "Docker Compose" in stack_values

    def test_empty_tree(self):
        """Test analysis of empty file tree."""
        discovery = GitHubDiscovery()

        result = discovery._analyze_file_tree(
            [], "owner", "repo", "https://github.com/owner/repo"
        )

        assert result["technical_stack"] == []
        assert result["openapi_files"] == []
        assert result["primary_language"] is None

    def test_detect_github_actions_workflow(self):
        """Test detection of GitHub Actions from workflows directory."""
        discovery = GitHubDiscovery()

        tree = [
            {"path": ".github/workflows/test.yml", "type": "blob"},
        ]

        result = discovery._analyze_file_tree(
            tree, "owner", "repo", "https://github.com/owner/repo"
        )

        assert any(
            fact.value == "GitHub Actions"
            for fact in result["technical_stack"]
        )

    def test_detect_docs_directory(self):
        """Test detection of docs directory."""
        discovery = GitHubDiscovery()

        tree = [
            {"path": "docs", "type": "tree"},
            {"path": "docs/api.md", "type": "blob"},
        ]

        result = discovery._analyze_file_tree(
            tree, "owner", "repo", "https://github.com/owner/repo"
        )

        assert "docs" in result["discovered_urls"]

    def test_ignore_duplicate_stack_items(self):
        """Test that duplicate stack items are not added twice."""
        discovery = GitHubDiscovery()

        tree = [
            {"path": "package.json", "type": "blob"},
            {"path": "package.json", "type": "blob"},  # Duplicate
        ]

        result = discovery._analyze_file_tree(
            tree, "owner", "repo", "https://github.com/owner/repo"
        )

        nodejs_count = sum(
            1 for fact in result["technical_stack"]
            if fact.value == "Node.js"
        )
        assert nodejs_count == 1

    def test_normalize_path_for_language_detection(self):
        """Test that language detection works with nested files."""
        discovery = GitHubDiscovery()

        tree = [
            {"path": "src/deeply/nested/file.rs", "type": "blob"},
            {"path": "src/main.go", "type": "blob"},
        ]

        result = discovery._analyze_file_tree(
            tree, "owner", "repo", "https://github.com/owner/repo"
        )

        # Both Rust and Go appear once, so one is primary (most_common returns first)
        assert result["primary_language"] in ["Rust", "Go"]


class TestGitHubDiscoveryIntegration:
    """Integration tests for GitHubDiscovery discovery method."""

    @patch('requests.get')
    def test_discover_invalid_url(self, mock_get):
        """Test discovery with invalid URL."""
        discovery = GitHubDiscovery()

        result = discovery.discover("https://example.com/not-github")

        assert result.success is False
        assert "parse" in result.error.lower()
        assert result.source_type == SourceType.GITHUB_REPO

    @patch('requests.get')
    def test_discover_repo_not_found(self, mock_get):
        """Test discovery when repo doesn't exist."""
        discovery = GitHubDiscovery()
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = {}

        result = discovery.discover("https://github.com/nonexistent/repo")

        assert result.success is False
        assert result.error is not None
        assert result.product_url == "https://github.com/nonexistent/repo"
