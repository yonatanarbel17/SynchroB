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
