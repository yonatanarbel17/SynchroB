"""
GitHub repository discovery source.

Queries the GitHub API to extract repository metadata, README content,
file tree structure, and infer technical stack from the repository layout.
"""

import base64
import json
import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.discovery.models import (
    SourceType,
    ConfidenceLevel,
    SourcedFact,
    SourcedEndpoint,
    SourceResult,
)

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
REQUEST_TIMEOUT = 10

# File extensions to language mapping for inferring primary language
EXTENSION_TO_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript (React)",
    ".tsx": "TypeScript (React)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".swift": "Swift",
    ".cpp": "C++",
    ".c": "C",
    ".scala": "Scala",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".hs": "Haskell",
    ".lua": "Lua",
    ".r": "R",
    ".R": "R",
    ".dart": "Dart",
}

# Build system / dependency files and what they indicate
STACK_INDICATOR_FILES = {
    "package.json": "Node.js",
    "setup.py": "Python (setuptools)",
    "pyproject.toml": "Python (modern packaging)",
    "setup.cfg": "Python (setuptools)",
    "Cargo.toml": "Rust (Cargo)",
    "go.mod": "Go (modules)",
    "Gemfile": "Ruby (Bundler)",
    "composer.json": "PHP (Composer)",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java/Kotlin (Gradle)",
    "build.gradle.kts": "Kotlin (Gradle KTS)",
    "Makefile": "Make",
    "CMakeLists.txt": "CMake",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    ".travis.yml": "Travis CI",
    ".github/workflows": "GitHub Actions",
    "Jenkinsfile": "Jenkins",
    "requirements.txt": "Python (pip)",
    "Pipfile": "Python (Pipenv)",
    "poetry.lock": "Python (Poetry)",
    "yarn.lock": "Yarn",
    "package-lock.json": "NPM",
    "tsconfig.json": "TypeScript",
}

# OpenAPI/Swagger file names to look for in the tree
OPENAPI_FILENAMES = {
    "openapi.json",
    "openapi.yaml",
    "openapi.yml",
    "swagger.json",
    "swagger.yaml",
    "swagger.yml",
}


class GitHubDiscovery:
    """
    Discovers product information from a GitHub repository using the
    GitHub REST API (v3).

    Extracts:
    - Repository metadata (description, language, topics)
    - README content and parsed capabilities
    - File tree analysis for technical stack inference
    - OpenAPI spec file locations
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize with an optional GitHub personal access token.

        Args:
            token: GitHub API token for higher rate limits and private repos.
        """
        self.headers: Dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    @staticmethod
    def _parse_repo_url(repo_url: str) -> Optional[Tuple[str, str]]:
        """
        Extract (owner, repo) from a GitHub URL.

        Handles:
            https://github.com/owner/repo
            https://github.com/owner/repo.git
            git+https://github.com/owner/repo.git
            git://github.com/owner/repo.git
            http://github.com/owner/repo/
            https://github.com/owner/repo/tree/main/...

        Returns None if the URL is not a valid GitHub repository URL.
        """
        url = repo_url.strip()

        # Remove git+ prefix
        if url.startswith("git+"):
            url = url[4:]

        # Convert git:// to https://
        if url.startswith("git://"):
            url = "https://" + url[6:]

        # Remove .git suffix
        if url.endswith(".git"):
            url = url[:-4]

        # Remove trailing slash
        url = url.rstrip("/")

        # Match github.com/owner/repo pattern
        match = re.match(
            r"https?://github\.com/([^/]+)/([^/]+?)(?:/.*)?$",
            url,
        )
        if match:
            owner = match.group(1)
            repo = match.group(2)
            # Skip non-repo paths
            if owner in ("topics", "explore", "settings", "organizations"):
                return None
            return (owner, repo)

        return None

    def _api_get(self, path: str) -> Optional[requests.Response]:
        """
        Make a GET request to the GitHub API with error handling.

        Returns the response on success, or None on error.
        Logs rate-limit warnings when appropriate.
        """
        url = f"{GITHUB_API_BASE}{path}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)

            # Check rate limiting
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining is not None and int(remaining) < 10:
                logger.warning(
                    "GitHub API rate limit low: %s requests remaining", remaining
                )

            if resp.status_code == 200:
                return resp
            elif resp.status_code == 403:
                logger.warning(
                    "GitHub API rate limited or forbidden for %s (remaining: %s)",
                    path,
                    remaining,
                )
                return None
            elif resp.status_code == 404:
                logger.debug("GitHub resource not found: %s", path)
                return None
            else:
                logger.warning(
                    "GitHub API returned %d for %s", resp.status_code, path
                )
                return None

        except requests.RequestException as exc:
            logger.debug("GitHub API request failed for %s: %s", path, exc)
            return None

    def _fetch_repo_metadata(
        self, owner: str, repo: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch basic repository metadata."""
        resp = self._api_get(f"/repos/{owner}/{repo}")
        if resp is None:
            return None
        return resp.json()

    def _fetch_readme(self, owner: str, repo: str) -> Optional[str]:
        """
        Fetch and decode the repository README content.
        Returns the decoded text or None.
        """
        resp = self._api_get(f"/repos/{owner}/{repo}/readme")
        if resp is None:
            return None

        data = resp.json()
        content_b64 = data.get("content", "")
        encoding = data.get("encoding", "")

        if encoding == "base64" and content_b64:
            try:
                return base64.b64decode(content_b64).decode("utf-8", errors="replace")
            except Exception as exc:
                logger.debug("Failed to decode README: %s", exc)
                return None

        return None

    def _parse_readme_capabilities(
        self, readme_text: str, source_url: str
    ) -> List[SourcedFact]:
        """
        Extract capabilities from README content by looking at headings
        and bullet points under relevant sections.
        """
        capabilities: List[SourcedFact] = []
        seen: set = set()

        # Sections that typically describe capabilities
        capability_headings = re.compile(
            r"^#{1,3}\s+"
            r"(Features|Capabilities|What it does|API|Endpoints|"
            r"Key Features|Highlights|Overview|Getting Started|"
            r"Why .+|About|What\'s included|Functionality)",
            re.IGNORECASE | re.MULTILINE,
        )

        lines = readme_text.split("\n")
        in_capability_section = False
        current_heading = ""

        for line in lines:
            stripped = line.strip()

            # Check if this is a heading
            heading_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
            if heading_match:
                heading_text = heading_match.group(2).strip()
                if capability_headings.match(stripped):
                    in_capability_section = True
                    current_heading = heading_text
                else:
                    in_capability_section = False
                continue

            if not in_capability_section:
                continue

            # Look for bullet points
            bullet_match = re.match(r"^[-*+]\s+(.+)$", stripped)
            if bullet_match:
                bullet_text = bullet_match.group(1).strip()
                # Remove markdown formatting
                bullet_text = re.sub(r"\*\*(.+?)\*\*", r"\1", bullet_text)
                bullet_text = re.sub(r"`(.+?)`", r"\1", bullet_text)
                # Remove trailing links
                bullet_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", bullet_text)
                bullet_text = bullet_text.strip()

                if bullet_text and len(bullet_text) > 3 and bullet_text not in seen:
                    seen.add(bullet_text)
                    capabilities.append(SourcedFact(
                        value=bullet_text,
                        source=SourceType.GITHUB_REPO,
                        source_url=source_url,
                        confidence=ConfidenceLevel.MEDIUM,
                        raw_evidence=f"README section '{current_heading}': {bullet_text}",
                    ))

        return capabilities

    def _fetch_file_tree(
        self, owner: str, repo: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch the full recursive file tree from the repository.
        Returns the list of tree entries or None.
        """
        resp = self._api_get(
            f"/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
        )
        if resp is None:
            return None

        data = resp.json()
        tree = data.get("tree", [])
        if not isinstance(tree, list):
            return None
        return tree

    def _analyze_file_tree(
        self, tree: List[Dict[str, Any]], owner: str, repo: str, source_url: str
    ) -> Dict[str, Any]:
        """
        Analyze the file tree to infer technical stack, find OpenAPI specs,
        docs directories, and primary languages.
        """
        result: Dict[str, Any] = {
            "technical_stack": [],
            "discovered_urls": {},
            "openapi_files": [],
            "primary_language": None,
        }
        seen_stack: set = set()
        ext_counter: Counter = Counter()

        for entry in tree:
            entry_path = entry.get("path", "")
            entry_type = entry.get("type", "")
            filename = entry_path.split("/")[-1] if entry_path else ""

            # Check for OpenAPI spec files
            if filename.lower() in OPENAPI_FILENAMES:
                result["openapi_files"].append(entry_path)
                raw_url = (
                    f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{entry_path}"
                )
                result["discovered_urls"]["openapi_spec_raw_url"] = raw_url
                result["discovered_urls"]["openapi_spec_file"] = entry_path

            # Check for docs directory
            if entry_type == "tree" and entry_path.lower() in (
                "docs", "doc", "documentation",
            ):
                result["discovered_urls"]["docs"] = (
                    f"https://github.com/{owner}/{repo}/tree/HEAD/{entry_path}"
                )

            # Also check for docs at any level (e.g. api/docs)
            if entry_type == "tree" and filename.lower() in ("docs", "doc"):
                docs_key = "docs"
                if docs_key not in result["discovered_urls"]:
                    result["discovered_urls"][docs_key] = (
                        f"https://github.com/{owner}/{repo}/tree/HEAD/{entry_path}"
                    )

            # Check for stack indicator files
            if filename in STACK_INDICATOR_FILES:
                stack_label = STACK_INDICATOR_FILES[filename]
                if stack_label not in seen_stack:
                    seen_stack.add(stack_label)
                    result["technical_stack"].append(SourcedFact(
                        value=stack_label,
                        source=SourceType.GITHUB_REPO,
                        source_url=source_url,
                        confidence=ConfidenceLevel.HIGH,
                        raw_evidence=f"File found in repo tree: {entry_path}",
                    ))

            # Also detect GitHub Actions workflows directory
            if entry_path.startswith(".github/workflows") and entry_type == "blob":
                ga_label = "GitHub Actions"
                if ga_label not in seen_stack:
                    seen_stack.add(ga_label)
                    result["technical_stack"].append(SourcedFact(
                        value=ga_label,
                        source=SourceType.GITHUB_REPO,
                        source_url=source_url,
                        confidence=ConfidenceLevel.HIGH,
                        raw_evidence=f"Workflow file: {entry_path}",
                    ))

            # Count file extensions for language inference
            if entry_type == "blob":
                ext_match = re.search(r"\.[a-zA-Z0-9]+$", filename)
                if ext_match:
                    ext = ext_match.group(0).lower()
                    if ext in EXTENSION_TO_LANGUAGE:
                        ext_counter[ext] += 1

        # Infer primary language from file extensions
        if ext_counter:
            most_common_ext = ext_counter.most_common(1)[0][0]
            result["primary_language"] = EXTENSION_TO_LANGUAGE.get(most_common_ext)

        return result

    def discover(self, repo_url: str) -> SourceResult:
        """
        Discover product information from a GitHub repository.

        Args:
            repo_url: A GitHub repository URL (various formats accepted).

        Returns:
            SourceResult with repository metadata, README-extracted
            capabilities, technical stack from file tree, and discovered URLs.
        """
        logger.info("GitHubDiscovery: analyzing %s", repo_url)

        parsed = self._parse_repo_url(repo_url)
        if parsed is None:
            logger.warning("Invalid GitHub URL: %s", repo_url)
            return SourceResult(
                source_type=SourceType.GITHUB_REPO,
                success=False,
                error=f"Could not parse GitHub repository URL: {repo_url}",
            )

        owner, repo = parsed
        source_url = f"https://github.com/{owner}/{repo}"

        # ---- 1. Repository metadata ----
        repo_meta = self._fetch_repo_metadata(owner, repo)
        if repo_meta is None:
            return SourceResult(
                source_type=SourceType.GITHUB_REPO,
                success=False,
                error=f"Could not fetch repository metadata for {owner}/{repo}",
                product_url=source_url,
            )

        description = repo_meta.get("description", "")
        language = repo_meta.get("language", "")
        topics = repo_meta.get("topics", []) or []
        homepage = repo_meta.get("homepage", "")
        html_url = repo_meta.get("html_url", source_url)

        # Build capabilities from topics
        capabilities: List[SourcedFact] = []
        for topic in topics:
            capabilities.append(SourcedFact(
                value=topic,
                source=SourceType.GITHUB_REPO,
                source_url=html_url,
                confidence=ConfidenceLevel.MEDIUM,
                raw_evidence=f"GitHub repository topic: {topic}",
            ))

        # Technical stack from primary language
        technical_stack: List[SourcedFact] = []
        if language:
            technical_stack.append(SourcedFact(
                value=language,
                source=SourceType.GITHUB_REPO,
                source_url=html_url,
                confidence=ConfidenceLevel.HIGH,
                raw_evidence=f"GitHub primary language: {language}",
            ))

        # Discovered URLs
        discovered_urls: Dict[str, str] = {
            "github_repo": html_url,
        }
        if homepage:
            discovered_urls["homepage"] = homepage

        # ---- 2. README ----
        raw_content = None
        readme_text = self._fetch_readme(owner, repo)
        if readme_text:
            raw_content = readme_text
            readme_capabilities = self._parse_readme_capabilities(
                readme_text, html_url
            )
            capabilities.extend(readme_capabilities)

        # ---- 3. File tree ----
        tree = self._fetch_file_tree(owner, repo)
        if tree is not None:
            tree_analysis = self._analyze_file_tree(tree, owner, repo, html_url)

            # Merge technical stack (avoid duplicates)
            existing_stack_values = {f.value for f in technical_stack}
            for fact in tree_analysis["technical_stack"]:
                if fact.value not in existing_stack_values:
                    technical_stack.append(fact)
                    existing_stack_values.add(fact.value)

            # Merge discovered URLs
            for key, url_val in tree_analysis["discovered_urls"].items():
                if key not in discovered_urls:
                    discovered_urls[key] = url_val

            # If primary language was not set by API, use file-tree inference
            if not language and tree_analysis["primary_language"]:
                inferred_lang = tree_analysis["primary_language"]
                if inferred_lang not in existing_stack_values:
                    technical_stack.append(SourcedFact(
                        value=inferred_lang,
                        source=SourceType.GITHUB_REPO,
                        source_url=html_url,
                        confidence=ConfidenceLevel.MEDIUM,
                        raw_evidence="Inferred from file extension counts in repository tree",
                    ))

        # SDK languages from technical stack
        sdk_languages: List[SourcedFact] = []
        sdk_lang_names = {
            "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java",
            "Ruby", "PHP", "C#", "Swift", "Kotlin", "Scala", "Elixir",
            "Dart", "R",
        }
        seen_sdk: set = set()
        for fact in technical_stack:
            # Check if the value starts with a known language name
            for lang in sdk_lang_names:
                if fact.value.startswith(lang) and lang not in seen_sdk:
                    seen_sdk.add(lang)
                    sdk_languages.append(SourcedFact(
                        value=lang,
                        source=SourceType.GITHUB_REPO,
                        source_url=html_url,
                        confidence=fact.confidence,
                        raw_evidence=fact.raw_evidence,
                    ))
        # Also add the primary language if not already covered
        if language and language not in seen_sdk:
            sdk_languages.append(SourcedFact(
                value=language,
                source=SourceType.GITHUB_REPO,
                source_url=html_url,
                confidence=ConfidenceLevel.HIGH,
                raw_evidence=f"GitHub primary language: {language}",
            ))

        logger.info(
            "GitHubDiscovery: found %d capabilities, %d stack items, %d URLs for %s/%s",
            len(capabilities),
            len(technical_stack),
            len(discovered_urls),
            owner,
            repo,
        )

        return SourceResult(
            source_type=SourceType.GITHUB_REPO,
            success=True,
            product_name=repo_meta.get("name", repo),
            product_url=html_url,
            description=description if description else None,
            capabilities=capabilities,
            sdk_languages=sdk_languages,
            technical_stack=technical_stack,
            discovered_urls=discovered_urls,
            raw_content=raw_content,
        )
