#!/usr/bin/env python3
"""
Deterministic repo structure extractor.

Clones a repo (or reads a local path), walks the file tree, and produces a
structured JSON bundle of everything the LLM needs to analyze the codebase:
  - File tree
  - Dependency manifests (parsed)
  - README content
  - OpenAPI/Swagger specs found on disk
  - Source code samples from key files (entry points, routes, models)
  - Configuration files (Docker, CI, env)

Usage:
    python extract_repo_structure.py <repo_path> [--output extraction.json]
    python extract_repo_structure.py --clone <github_url> [--output extraction.json]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Max characters to read from any single source file
SOURCE_SAMPLE_LIMIT = 6000

# Max total characters for all source samples combined
TOTAL_SOURCE_LIMIT = 80000

# Dependency manifest filenames and their ecosystem
DEPENDENCY_FILES = {
    "package.json": "npm",
    "package-lock.json": "npm-lock",
    "yarn.lock": "yarn",
    "requirements.txt": "pip",
    "Pipfile": "pipenv",
    "Pipfile.lock": "pipenv-lock",
    "pyproject.toml": "python-modern",
    "setup.py": "setuptools",
    "setup.cfg": "setuptools",
    "poetry.lock": "poetry",
    "go.mod": "go",
    "go.sum": "go-sum",
    "Cargo.toml": "rust",
    "Cargo.lock": "rust-lock",
    "Gemfile": "ruby",
    "Gemfile.lock": "ruby-lock",
    "composer.json": "php",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle-kts",
    "pom.xml": "maven",
    "mix.exs": "elixir",
    "pubspec.yaml": "dart",
}

# Config / infra files worth capturing
CONFIG_FILES = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env.example",
    ".env.template",
    ".env.sample",
    "Makefile",
    "Procfile",
    "serverless.yml",
    "serverless.yaml",
    "terraform.tf",
    "app.yaml",
    "fly.toml",
    "render.yaml",
    "vercel.json",
    "netlify.toml",
}

# CI/CD config patterns
CI_PATTERNS = [
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    ".circleci/config.yml",
    ".travis.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
]

# OpenAPI/Swagger filenames
OPENAPI_FILENAMES = {
    "openapi.json", "openapi.yaml", "openapi.yml",
    "swagger.json", "swagger.yaml", "swagger.yml",
}

# File extensions for source code
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".kt",
    ".rb", ".php", ".cs", ".swift", ".scala", ".ex", ".exs", ".hs",
    ".lua", ".r", ".dart", ".cpp", ".c", ".h",
}

# Directories to skip entirely
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".tox", ".mypy_cache",
    ".pytest_cache", "venv", ".venv", "env", ".env", "vendor",
    "dist", "build", ".next", ".nuxt", "target", "coverage",
    ".terraform", ".serverless",
}

# Filenames that suggest "entry point"
ENTRY_POINT_PATTERNS = [
    "main.py", "app.py", "server.py", "index.py", "wsgi.py", "asgi.py",
    "manage.py", "__main__.py",
    "main.ts", "main.js", "index.ts", "index.js", "server.ts", "server.js",
    "app.ts", "app.js",
    "main.go", "cmd/*/main.go",
    "main.rs", "lib.rs",
    "Main.java", "Application.java",
    "main.rb", "app.rb", "config.ru",
]

# Path patterns that suggest route/handler definitions
ROUTE_PATTERNS = [
    r"routes?[/\\]", r"handlers?[/\\]", r"controllers?[/\\]",
    r"views?[/\\]", r"endpoints?[/\\]", r"api[/\\]",
    r"router", r"urls\.py",
]

# Path patterns for model/schema definitions
MODEL_PATTERNS = [
    r"models?[/\\]", r"schemas?[/\\]", r"entities[/\\]",
    r"types?[/\\]", r"domain[/\\]",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clone_repo(url: str, target_dir: str) -> str:
    """Clone a git repo to target_dir. Returns the repo path."""
    # Shallow clone for speed
    subprocess.run(
        ["git", "clone", "--depth", "1", url, target_dir],
        check=True,
        capture_output=True,
        text=True,
    )
    return target_dir


def walk_file_tree(repo_path: str) -> List[str]:
    """Walk the repo and return all file paths (relative to repo root)."""
    files = []
    root = Path(repo_path)
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out skip directories in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = Path(dirpath).relative_to(root)
        for fname in filenames:
            rel_path = str(rel_dir / fname)
            if rel_path.startswith("."):
                # Skip hidden files at root except known configs
                basename = fname
                if basename not in CONFIG_FILES and not basename.startswith(".github"):
                    if not any(basename == cf for cf in DEPENDENCY_FILES):
                        continue
            files.append(rel_path)
    return sorted(files)


def read_file_safe(path: str, limit: int = SOURCE_SAMPLE_LIMIT) -> Optional[str]:
    """Read a file, returning None if binary or unreadable."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(limit)
        # Check if it looks binary
        if "\x00" in content[:1000]:
            return None
        return content
    except (OSError, UnicodeDecodeError):
        return None


def find_matching_files(file_tree: List[str], patterns: List[str]) -> List[str]:
    """Find files matching any of the regex patterns."""
    matches = []
    for fpath in file_tree:
        for pattern in patterns:
            if re.search(pattern, fpath, re.IGNORECASE):
                matches.append(fpath)
                break
    return matches


def is_entry_point(fpath: str) -> bool:
    """Check if a file path looks like an entry point."""
    basename = os.path.basename(fpath)
    for pattern in ENTRY_POINT_PATTERNS:
        if "*" in pattern:
            regex = pattern.replace("*", "[^/]+")
            if re.match(regex, fpath):
                return True
        elif basename == pattern:
            return True
    return False


def extract_dependencies(repo_path: str, file_tree: List[str]) -> Dict[str, Any]:
    """Extract and parse dependency manifests."""
    deps = {}
    for fpath in file_tree:
        basename = os.path.basename(fpath)
        if basename in DEPENDENCY_FILES:
            full_path = os.path.join(repo_path, fpath)
            content = read_file_safe(full_path, limit=20000)
            if content is None:
                continue

            ecosystem = DEPENDENCY_FILES[basename]
            entry = {"file": fpath, "ecosystem": ecosystem, "raw": content}

            # Try to parse structured formats
            if basename == "package.json":
                try:
                    parsed = json.loads(content)
                    entry["parsed"] = {
                        "name": parsed.get("name"),
                        "description": parsed.get("description"),
                        "dependencies": parsed.get("dependencies", {}),
                        "devDependencies": parsed.get("devDependencies", {}),
                        "scripts": parsed.get("scripts", {}),
                        "engines": parsed.get("engines", {}),
                    }
                except json.JSONDecodeError:
                    pass
            elif basename == "requirements.txt":
                lines = [
                    l.strip() for l in content.splitlines()
                    if l.strip() and not l.strip().startswith("#")
                ]
                entry["parsed"] = {"packages": lines}

            deps[fpath] = entry
    return deps


def extract_openapi_specs(repo_path: str, file_tree: List[str]) -> Dict[str, Any]:
    """Find and read OpenAPI/Swagger spec files."""
    specs = {}
    for fpath in file_tree:
        basename = os.path.basename(fpath).lower()
        if basename in OPENAPI_FILENAMES:
            full_path = os.path.join(repo_path, fpath)
            content = read_file_safe(full_path, limit=50000)
            if content is None:
                continue
            entry = {"file": fpath, "raw": content}
            if basename.endswith(".json"):
                try:
                    entry["parsed"] = json.loads(content)
                except json.JSONDecodeError:
                    pass
            specs[fpath] = entry
    return specs


def extract_readme(repo_path: str, file_tree: List[str]) -> Optional[str]:
    """Find and read the README."""
    readme_names = ["README.md", "readme.md", "README.rst", "README.txt", "README"]
    for name in readme_names:
        if name in file_tree:
            return read_file_safe(os.path.join(repo_path, name), limit=15000)
    # Also check case-insensitive
    for fpath in file_tree:
        if os.path.basename(fpath).lower().startswith("readme"):
            return read_file_safe(os.path.join(repo_path, fpath), limit=15000)
    return None


def extract_config_files(repo_path: str, file_tree: List[str]) -> Dict[str, str]:
    """Read configuration and infrastructure files."""
    configs = {}
    for fpath in file_tree:
        basename = os.path.basename(fpath)
        # Direct config file matches
        if basename in CONFIG_FILES:
            content = read_file_safe(os.path.join(repo_path, fpath), limit=5000)
            if content:
                configs[fpath] = content
        # CI/CD files
        elif fpath.startswith(".github/workflows/") and (fpath.endswith(".yml") or fpath.endswith(".yaml")):
            content = read_file_safe(os.path.join(repo_path, fpath), limit=5000)
            if content:
                configs[fpath] = content
        elif basename in (".gitlab-ci.yml", ".travis.yml", "Jenkinsfile", "azure-pipelines.yml"):
            content = read_file_safe(os.path.join(repo_path, fpath), limit=5000)
            if content:
                configs[fpath] = content
    return configs


def select_source_samples(
    repo_path: str, file_tree: List[str]
) -> Dict[str, str]:
    """
    Select and read the most important source files.

    Priority order:
    1. Entry points (main.py, index.ts, etc.)
    2. Route/handler definitions
    3. Model/schema definitions
    4. Other source files (by directory depth — shallower = more important)

    Stays within TOTAL_SOURCE_LIMIT.
    """
    source_files = [
        f for f in file_tree
        if any(f.endswith(ext) for ext in SOURCE_EXTENSIONS)
    ]

    # Categorize
    entry_points = [f for f in source_files if is_entry_point(f)]
    route_files = find_matching_files(source_files, ROUTE_PATTERNS)
    model_files = find_matching_files(source_files, MODEL_PATTERNS)

    # Remove duplicates while preserving priority order
    seen = set()
    ordered = []
    for group in [entry_points, route_files, model_files]:
        for f in group:
            if f not in seen:
                seen.add(f)
                ordered.append(f)

    # Add remaining source files sorted by depth (shallower first)
    remaining = [f for f in source_files if f not in seen]
    remaining.sort(key=lambda f: (f.count("/"), f))
    ordered.extend(remaining)

    # Read files up to the total limit
    samples = {}
    total_chars = 0
    for fpath in ordered:
        if total_chars >= TOTAL_SOURCE_LIMIT:
            break
        content = read_file_safe(
            os.path.join(repo_path, fpath),
            limit=min(SOURCE_SAMPLE_LIMIT, TOTAL_SOURCE_LIMIT - total_chars),
        )
        if content and len(content.strip()) > 10:
            samples[fpath] = content
            total_chars += len(content)

    return samples


def count_files_by_extension(file_tree: List[str]) -> Dict[str, int]:
    """Count files by extension for language distribution."""
    counts: Dict[str, int] = {}
    for fpath in file_tree:
        ext = os.path.splitext(fpath)[1].lower()
        if ext in SOURCE_EXTENSIONS:
            counts[ext] = counts.get(ext, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def extract_docs(repo_path: str, file_tree: List[str]) -> Dict[str, Any]:
    """
    Extract documentation files that contain architecture and design info.
    Looks for CONTRIBUTING.md, ARCHITECTURE.md, DESIGN.md, HACKING.md, etc.
    Limits each file to 8000 characters.
    """
    docs = {}
    doc_filenames = {
        "CONTRIBUTING.md", "ARCHITECTURE.md", "DESIGN.md", "HACKING.md",
        "contributing.md", "architecture.md", "design.md", "hacking.md",
        "docs/ARCHITECTURE.md", "docs/architecture.md", "docs/DESIGN.md",
        "docs/design.md", "docs/CONTRIBUTING.md", "docs/contributing.md",
    }

    # Check for exact filename matches
    for fpath in file_tree:
        basename = os.path.basename(fpath)
        dirname_basename = str(Path(fpath).parent / basename)

        if basename in doc_filenames or fpath in doc_filenames:
            full_path = os.path.join(repo_path, fpath)
            content = read_file_safe(full_path, limit=8000)
            if content:
                docs[fpath] = content

    # Also check case-insensitive pattern matching
    for fpath in file_tree:
        basename = os.path.basename(fpath).lower()
        if any(basename == d.lower() for d in ["contributing.md", "architecture.md", "design.md", "hacking.md"]):
            if fpath not in docs:
                full_path = os.path.join(repo_path, fpath)
                content = read_file_safe(full_path, limit=8000)
                if content:
                    docs[fpath] = content

    return docs


def detect_license(repo_path: str, file_tree: List[str]) -> Optional[str]:
    """
    Detect license type by reading LICENSE, LICENSE.md, COPYING files.
    Returns the detected license type (MIT, Apache-2.0, GPL-3.0, etc.) or None.
    """
    license_filenames = {
        "LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md",
        "license", "license.md", "license.txt", "copying", "copying.md",
    }

    license_content = None
    for fpath in file_tree:
        basename = os.path.basename(fpath)
        if basename in license_filenames or basename.lower() in {f.lower() for f in license_filenames}:
            full_path = os.path.join(repo_path, fpath)
            content = read_file_safe(full_path, limit=5000)
            if content:
                license_content = content
                break

    if not license_content:
        return None

    # Check for common license strings
    license_lower = license_content.lower()

    # SPDX identifier patterns
    if "mit license" in license_lower or "permission is hereby granted, free of charge" in license_lower:
        return "MIT"
    elif "apache license" in license_lower and "version 2.0" in license_lower:
        return "Apache-2.0"
    elif "gnu general public license" in license_lower and "version 3" in license_lower:
        return "GPL-3.0"
    elif "gnu general public license" in license_lower and "version 2" in license_lower:
        return "GPL-2.0"
    elif "bsd" in license_lower and "3-clause" in license_lower:
        return "BSD-3-Clause"
    elif "bsd" in license_lower and "2-clause" in license_lower:
        return "BSD-2-Clause"
    elif "bsd" in license_lower:
        return "BSD"
    elif "mozilla public license" in license_lower:
        return "MPL-2.0"
    elif "creative commons" in license_lower:
        return "CC0-1.0"
    elif "isc license" in license_lower or "isc" in license_lower and "permission" in license_lower:
        return "ISC"
    elif "agpl" in license_lower:
        return "AGPL-3.0"
    elif "unlicense" in license_lower:
        return "Unlicense"

    return "Custom/Other"


def extract_git_metadata(repo_path: str) -> Dict[str, Any]:
    """
    Extract git metadata: recent commits, top contributors, total commit count,
    and repo creation date.
    """
    metadata = {}

    try:
        # Check if this is a git repository
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            return metadata
    except (OSError, subprocess.CalledProcessError):
        return metadata

    try:
        # Get recent commits
        result = subprocess.run(
            ["git", "-C", repo_path, "log", "--oneline", "-20"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            commits = result.stdout.strip().split("\n") if result.stdout.strip() else []
            metadata["recent_commits"] = commits
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    try:
        # Get top contributors
        result = subprocess.run(
            ["git", "-C", repo_path, "log", "--format=%aN"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            authors = result.stdout.strip().split("\n") if result.stdout.strip() else []
            # Count occurrences
            author_counts: Dict[str, int] = {}
            for author in authors:
                if author.strip():
                    author_counts[author.strip()] = author_counts.get(author.strip(), 0) + 1
            # Sort by count descending
            top_authors = sorted(author_counts.items(), key=lambda x: -x[1])[:10]
            metadata["top_contributors"] = [{"name": name, "commits": count} for name, count in top_authors]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    try:
        # Get total commit count
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            metadata["total_commits"] = int(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
        pass

    try:
        # Get repo creation date
        result = subprocess.run(
            ["git", "-C", repo_path, "log", "--reverse", "--format=%ci"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            dates = result.stdout.strip().split("\n") if result.stdout.strip() else []
            if dates and dates[0]:
                metadata["creation_date"] = dates[0]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return metadata


def extract_test_info(repo_path: str, file_tree: List[str]) -> Dict[str, Any]:
    """
    Extract test information: test file locations, frameworks detected, test count.
    Looks for test/ tests/ spec/ __tests__/ and files matching test patterns.
    """
    test_info = {
        "test_files": [],
        "test_frameworks": [],
        "test_file_count": 0,
    }

    # Test directory patterns
    test_dirs = {"test", "tests", "spec", "__tests__"}
    test_patterns = [
        r"_test\.py$", r"_test\.go$",
        r"^test_.*\.py$", r"test.*\.java$",
        r"\.test\.ts$", r"\.test\.js$",
        r"\.spec\.ts$", r"\.spec\.js$",
    ]

    test_files = []
    for fpath in file_tree:
        parts = Path(fpath).parts
        # Check if in test directory
        if any(part in test_dirs for part in parts):
            test_files.append(fpath)
        else:
            # Check filename patterns
            for pattern in test_patterns:
                if re.search(pattern, fpath):
                    test_files.append(fpath)
                    break

    test_info["test_files"] = test_files[:3]  # Sample 2-3 test file paths
    test_info["test_file_count"] = len(test_files)

    # Detect test frameworks from package.json and imports
    test_frameworks = set()

    # Check package.json for test scripts and dependencies
    for fpath in file_tree:
        if os.path.basename(fpath) == "package.json":
            full_path = os.path.join(repo_path, fpath)
            content = read_file_safe(full_path, limit=20000)
            if content:
                try:
                    parsed = json.loads(content)
                    # Check test scripts
                    scripts = parsed.get("scripts", {})
                    for script_name, script_content in scripts.items():
                        if "jest" in script_content.lower():
                            test_frameworks.add("Jest")
                        if "mocha" in script_content.lower():
                            test_frameworks.add("Mocha")
                        if "vitest" in script_content.lower():
                            test_frameworks.add("Vitest")
                        if "cypress" in script_content.lower():
                            test_frameworks.add("Cypress")

                    # Check dependencies
                    deps = {**parsed.get("dependencies", {}), **parsed.get("devDependencies", {})}
                    if "jest" in deps:
                        test_frameworks.add("Jest")
                    if "mocha" in deps:
                        test_frameworks.add("Mocha")
                    if "vitest" in deps:
                        test_frameworks.add("Vitest")
                    if "cypress" in deps:
                        test_frameworks.add("Cypress")
                    if "@testing-library/react" in deps or "@testing-library/vue" in deps:
                        test_frameworks.add("Testing Library")
                except json.JSONDecodeError:
                    pass

    # Check for pytest, unittest, nose in Python files
    if any(".py" in f for f in file_tree):
        for fpath in test_files[:5]:
            if fpath.endswith(".py"):
                full_path = os.path.join(repo_path, fpath)
                content = read_file_safe(full_path, limit=2000)
                if content:
                    if "import pytest" in content or "from pytest" in content:
                        test_frameworks.add("pytest")
                    if "import unittest" in content or "from unittest" in content:
                        test_frameworks.add("unittest")
                    if "import nose" in content:
                        test_frameworks.add("nose")

    # Check for Go testing
    if any(".go" in f for f in test_files):
        test_frameworks.add("Go testing")

    # Check for Rust testing
    if any(".rs" in f for f in test_files):
        test_frameworks.add("Rust testing")

    test_info["test_frameworks"] = list(test_frameworks)

    return test_info


def detect_plugin_system(repo_path: str, file_tree: List[str]) -> Dict[str, Any]:
    """
    Detect plugin/extension architecture patterns.
    Looks for plugins/, extensions/, addons/ directories and related patterns.
    """
    plugin_info = {
        "has_plugin_system": False,
        "plugin_indicators": [],
        "plugin_directories": [],
    }

    plugin_dirs = {"plugins", "extensions", "addons", "middleware", "modules"}
    hook_patterns = [
        r"hook", r"event.*emitter", r"publish.*subscribe",
        r"observer.*pattern", r"handler", r"middleware",
    ]

    # Check for plugin directories
    for fpath in file_tree:
        parts = Path(fpath).parts
        if any(part in plugin_dirs for part in parts):
            plugin_info["has_plugin_system"] = True
            dir_path = str(Path(fpath).parent)
            if dir_path not in plugin_info["plugin_directories"]:
                plugin_info["plugin_directories"].append(dir_path)

    # Check for hook/event patterns in source files
    hook_files = []
    for fpath in file_tree:
        if any(fpath.endswith(ext) for ext in SOURCE_EXTENSIONS):
            for pattern in hook_patterns:
                if re.search(pattern, fpath, re.IGNORECASE):
                    hook_files.append(fpath)
                    break

    if hook_files:
        plugin_info["has_plugin_system"] = True
        plugin_info["plugin_indicators"].extend(hook_files[:3])

    # Look for common plugin interface patterns in code
    for fpath in hook_files[:3]:
        full_path = os.path.join(repo_path, fpath)
        content = read_file_safe(full_path, limit=3000)
        if content:
            if "interface" in content.lower() or "abstract" in content.lower():
                if "plugin" not in plugin_info["plugin_indicators"]:
                    plugin_info["plugin_indicators"].append(f"Found plugin-like interfaces in {fpath}")

    return plugin_info


def extract_db_schemas(repo_path: str, file_tree: List[str]) -> Dict[str, Any]:
    """
    Extract database schema information from migrations, ORM models, and SQL files.
    Looks for migrations/, alembic/, db/migrate/ and model files.
    Reads up to 3 files, max 3000 chars each.
    """
    db_info = {
        "migration_files": [],
        "orm_models": [],
        "sql_schemas": [],
        "migration_samples": {},
    }

    migration_dirs = {"migrations", "alembic", "migrate"}
    migration_extensions = {".sql", ".py"}
    orm_patterns = [
        r"models?[/\\].*\.(py|js|ts|java|go|rs)$",
        r"entities?[/\\].*\.(py|js|ts|java|go|rs)$",
    ]

    # Find migration files
    for fpath in file_tree:
        parts = Path(fpath).parts
        # Check if in migration directory
        if any(part in migration_dirs for part in parts):
            db_info["migration_files"].append(fpath)
        # Check for SQL schema files
        elif fpath.endswith(".sql") and any(
            part in {"db", "schema", "sql", "database"} for part in parts[:2]
        ):
            db_info["sql_schemas"].append(fpath)

    # Find ORM models
    orm_files = find_matching_files(file_tree, orm_patterns)
    db_info["orm_models"] = orm_files[:3]

    # Read samples from migration and schema files
    all_schema_files = db_info["migration_files"] + db_info["sql_schemas"] + db_info["orm_models"]
    for fpath in all_schema_files[:3]:
        full_path = os.path.join(repo_path, fpath)
        content = read_file_safe(full_path, limit=3000)
        if content:
            db_info["migration_samples"][fpath] = content

    return db_info


def summarize_directory_structure(file_tree: List[str]) -> Dict[str, Any]:
    """
    Generate a 3-level deep directory tree structure for architecture overview.
    Similar to 'tree -L 3 -d'.
    """
    tree_dict: Dict[str, Any] = {}

    # Build directory tree up to 3 levels
    for fpath in file_tree:
        parts = Path(fpath).parts
        if len(parts) > 3:
            parts = parts[:3]

        current = tree_dict
        for i, part in enumerate(parts[:-1]):  # Exclude filename
            if part not in current:
                current[part] = {}
            current = current[part]

    return {"directory_tree": tree_dict, "depth_limit": 3}


def extract_community_health(repo_path: str, file_tree: List[str]) -> Dict[str, bool]:
    """
    Check for community health signals:
    CODE_OF_CONDUCT.md, SECURITY.md, issue templates, PR templates, FUNDING.yml
    """
    health = {
        "has_code_of_conduct": False,
        "has_security_policy": False,
        "has_issue_templates": False,
        "has_pr_templates": False,
        "has_funding_file": False,
        "files_found": [],
    }

    health_files = {
        "CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT.txt", "code_of_conduct.md",
        "SECURITY.md", "security.md", "SECURITY.txt",
        ".github/ISSUE_TEMPLATE/", ".github/PULL_REQUEST_TEMPLATE/",
        ".github/FUNDING.yml", ".github/funding.yml",
    }

    for fpath in file_tree:
        basename = os.path.basename(fpath)

        if "CODE_OF_CONDUCT" in basename.upper():
            health["has_code_of_conduct"] = True
            health["files_found"].append(fpath)
        elif "SECURITY" in basename.upper():
            health["has_security_policy"] = True
            health["files_found"].append(fpath)
        elif "ISSUE_TEMPLATE" in fpath.upper():
            health["has_issue_templates"] = True
            if fpath not in health["files_found"]:
                health["files_found"].append(fpath)
        elif "PULL_REQUEST_TEMPLATE" in fpath.upper():
            health["has_pr_templates"] = True
            if fpath not in health["files_found"]:
                health["files_found"].append(fpath)
        elif "FUNDING" in basename.upper() and fpath.startswith(".github"):
            health["has_funding_file"] = True
            health["files_found"].append(fpath)

    return health


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_repo(repo_path: str) -> Dict[str, Any]:
    """
    Perform full extraction of a repository.

    Returns a structured dict ready for LLM consumption.
    """
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        raise FileNotFoundError(f"Repository path not found: {repo_path}")

    file_tree = walk_file_tree(repo_path)

    extraction = {
        "repo_path": repo_path,
        "repo_name": os.path.basename(repo_path),
        "total_files": len(file_tree),
        "file_tree": file_tree,
        "language_distribution": count_files_by_extension(file_tree),
        "readme": extract_readme(repo_path, file_tree),
        "dependencies": extract_dependencies(repo_path, file_tree),
        "openapi_specs": extract_openapi_specs(repo_path, file_tree),
        "config_files": extract_config_files(repo_path, file_tree),
        "source_samples": select_source_samples(repo_path, file_tree),
        "docs": extract_docs(repo_path, file_tree),
        "license": detect_license(repo_path, file_tree),
        "git_metadata": extract_git_metadata(repo_path),
        "test_info": extract_test_info(repo_path, file_tree),
        "plugin_system": detect_plugin_system(repo_path, file_tree),
        "db_schemas": extract_db_schemas(repo_path, file_tree),
        "directory_structure": summarize_directory_structure(file_tree),
        "community_health": extract_community_health(repo_path, file_tree),
    }

    return extraction


def clone_and_extract(github_url: str, keep_repo: bool = False) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Clone a repo to a temp directory, extract it, and optionally clean up.

    Returns (extraction_dict, repo_path_if_kept_or_None).
    """
    tmpdir = tempfile.mkdtemp(prefix="synchrob_repo_")
    repo_name = github_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join(tmpdir, repo_name)

    try:
        clone_repo(github_url, repo_path)
        extraction = extract_repo(repo_path)

        if keep_repo:
            return extraction, repo_path
        else:
            return extraction, None
    finally:
        if not keep_repo:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract repository structure for LLM analysis."
    )
    parser.add_argument(
        "repo_path",
        nargs="?",
        help="Path to a local repo directory.",
    )
    parser.add_argument(
        "--clone",
        type=str,
        default=None,
        help="GitHub URL to clone instead of using a local path.",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output JSON file path (default: stdout).",
    )

    args = parser.parse_args()

    if args.clone:
        extraction, _ = clone_and_extract(args.clone, keep_repo=False)
    elif args.repo_path:
        extraction = extract_repo(args.repo_path)
    else:
        parser.error("Provide either a repo_path or --clone <url>")
        return 1

    output = json.dumps(extraction, indent=2, default=str)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Extraction saved to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
