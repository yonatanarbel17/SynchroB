"""
Package registry discovery source.

Queries PyPI and NPM registries to extract authoritative metadata about
a product's packages: descriptions, dependencies, URLs, and technical stack.
"""

import logging
import re
from typing import List, Optional

import requests

from src.discovery.models import (
    SourceType,
    ConfidenceLevel,
    SourcedFact,
    SourcedEndpoint,
    SourceResult,
)

logger = logging.getLogger(__name__)

PYPI_BASE = "https://pypi.org/pypi"
NPM_BASE = "https://registry.npmjs.org"
REQUEST_TIMEOUT = 10


class PackageRegistryDiscovery:
    """
    Discovers product information from PyPI and NPM package registries.

    Package registries are authoritative sources: if a package exists there,
    the metadata (description, dependencies, URLs) is highly reliable.
    """

    def _generate_name_variants(self, product_name: str) -> List[str]:
        """
        Generate plausible package name variants from a product name.

        Example: "Stripe" -> ["stripe", "stripe-python", "stripe-js",
                               "stripe-sdk", "pystripe"]
        Example: "My Product" -> ["my-product", "my_product", "myproduct",
                                   "my-product-python", ...]
        """
        base = product_name.strip().lower()
        # Replace any whitespace sequences with a single token for splitting
        parts = re.split(r"\s+", base)

        hyphenated = "-".join(parts)
        underscored = "_".join(parts)
        joined = "".join(parts)

        variants = list(dict.fromkeys([
            hyphenated,
            underscored,
            joined,
            f"{hyphenated}-python",
            f"{hyphenated}-js",
            f"{hyphenated}-sdk",
            f"py{joined}",
        ]))

        return variants

    def _clean_github_url(self, url: str) -> Optional[str]:
        """
        Normalize a GitHub URL by removing git+ prefix and .git suffix.
        Returns None if the URL is not GitHub.
        """
        if not url:
            return None
        cleaned = url.strip()
        # Remove git+ prefix
        if cleaned.startswith("git+"):
            cleaned = cleaned[4:]
        # Remove git:// and convert to https://
        if cleaned.startswith("git://"):
            cleaned = "https://" + cleaned[6:]
        # Remove .git suffix
        if cleaned.endswith(".git"):
            cleaned = cleaned[:-4]
        # Remove trailing slashes
        cleaned = cleaned.rstrip("/")
        if "github.com" in cleaned:
            return cleaned
        return None

    def _query_pypi(self, name: str) -> Optional[dict]:
        """
        Query PyPI for package metadata.
        Returns parsed JSON on success, None on failure.
        """
        url = f"{PYPI_BASE}/{name}/json"
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            # 404 means the package doesn't exist under this name
            return None
        except requests.RequestException as exc:
            logger.debug("PyPI request failed for %s: %s", name, exc)
            return None

    def _query_npm(self, name: str) -> Optional[dict]:
        """
        Query NPM for package metadata.
        Returns parsed JSON on success, None on failure.
        """
        url = f"{NPM_BASE}/{name}"
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.RequestException as exc:
            logger.debug("NPM request failed for %s: %s", name, exc)
            return None

    def _extract_pypi_facts(self, data: dict, variant: str) -> dict:
        """
        Extract structured facts from a PyPI JSON response.
        Returns a dict with lists of SourcedFact and other metadata.
        """
        info = data.get("info", {})
        source_url = f"https://pypi.org/project/{variant}/"
        result = {
            "description": None,
            "capabilities": [],
            "dependencies": [],
            "technical_stack": [],
            "discovered_urls": {},
            "sdk_languages": [],
        }

        # Description
        summary = info.get("summary", "")
        if summary:
            result["description"] = summary

        # Keywords -> capabilities
        keywords = info.get("keywords", "")
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
            for kw in keyword_list:
                result["capabilities"].append(SourcedFact(
                    value=kw,
                    source=SourceType.PACKAGE_REGISTRY,
                    source_url=source_url,
                    confidence=ConfidenceLevel.HIGH,
                    raw_evidence=f"PyPI keyword for package '{variant}'",
                ))

        # Dependencies
        requires_dist = info.get("requires_dist") or []
        for dep in requires_dist:
            # Extract just the package name (before version specifiers or extras)
            dep_name = re.split(r"[\s;(><=!~\[]", dep)[0].strip()
            if dep_name:
                result["dependencies"].append(SourcedFact(
                    value=dep_name,
                    source=SourceType.PACKAGE_REGISTRY,
                    source_url=source_url,
                    confidence=ConfidenceLevel.HIGH,
                    raw_evidence=f"PyPI requires_dist: {dep}",
                ))

        # Project URLs -> discovered_urls
        project_urls = info.get("project_urls") or {}
        url_key_mapping = {
            "Source": "github_repo",
            "Repository": "github_repo",
            "source": "github_repo",
            "repository": "github_repo",
            "Code": "github_repo",
            "GitHub": "github_repo",
            "Homepage": "homepage",
            "homepage": "homepage",
            "Home": "homepage",
            "Documentation": "docs",
            "documentation": "docs",
            "Docs": "docs",
            "docs": "docs",
            "Bug Tracker": "issues",
            "Issues": "issues",
            "Changelog": "changelog",
        }
        for key, url_val in project_urls.items():
            if url_val:
                mapped_key = url_key_mapping.get(key)
                if mapped_key:
                    final_url = url_val
                    if mapped_key == "github_repo":
                        cleaned = self._clean_github_url(url_val)
                        if cleaned:
                            final_url = cleaned
                    result["discovered_urls"][mapped_key] = final_url
                # Also check if any URL is a GitHub URL even if key not mapped
                github_url = self._clean_github_url(url_val)
                if github_url and "github_repo" not in result["discovered_urls"]:
                    result["discovered_urls"]["github_repo"] = github_url

        # Classifiers -> Python versions as technical_stack
        classifiers = info.get("classifiers") or []
        for classifier in classifiers:
            if classifier.startswith("Programming Language :: Python :: "):
                version = classifier.replace("Programming Language :: Python :: ", "")
                if version and re.match(r"^\d", version):
                    result["technical_stack"].append(SourcedFact(
                        value=f"Python {version}",
                        source=SourceType.PACKAGE_REGISTRY,
                        source_url=source_url,
                        confidence=ConfidenceLevel.HIGH,
                        raw_evidence=f"PyPI classifier: {classifier}",
                    ))

        # This is a Python package
        result["sdk_languages"].append(SourcedFact(
            value="Python",
            source=SourceType.PACKAGE_REGISTRY,
            source_url=source_url,
            confidence=ConfidenceLevel.HIGH,
            raw_evidence=f"Package '{variant}' found on PyPI",
        ))

        return result

    def _extract_npm_facts(self, data: dict, variant: str) -> dict:
        """
        Extract structured facts from an NPM JSON response.
        Returns a dict with lists of SourcedFact and other metadata.
        """
        source_url = f"https://www.npmjs.com/package/{variant}"
        result = {
            "description": None,
            "capabilities": [],
            "dependencies": [],
            "technical_stack": [],
            "discovered_urls": {},
            "sdk_languages": [],
            "raw_content": None,
        }

        # Description
        description = data.get("description", "")
        if description:
            result["description"] = description

        # Keywords -> capabilities
        keywords = data.get("keywords") or []
        for kw in keywords:
            if kw and isinstance(kw, str):
                result["capabilities"].append(SourcedFact(
                    value=kw.strip(),
                    source=SourceType.PACKAGE_REGISTRY,
                    source_url=source_url,
                    confidence=ConfidenceLevel.HIGH,
                    raw_evidence=f"NPM keyword for package '{variant}'",
                ))

        # Dependencies (latest version)
        latest_version = data.get("dist-tags", {}).get("latest", "")
        versions = data.get("versions", {})
        latest_data = versions.get(latest_version, {})
        deps = latest_data.get("dependencies") or data.get("dependencies") or {}
        if isinstance(deps, dict):
            for dep_name in deps.keys():
                result["dependencies"].append(SourcedFact(
                    value=dep_name,
                    source=SourceType.PACKAGE_REGISTRY,
                    source_url=source_url,
                    confidence=ConfidenceLevel.HIGH,
                    raw_evidence=f"NPM dependency: {dep_name}@{deps[dep_name]}",
                ))

        # Repository URL -> discovered_urls
        repository = data.get("repository") or {}
        if isinstance(repository, dict):
            repo_url = repository.get("url", "")
        elif isinstance(repository, str):
            repo_url = repository
        else:
            repo_url = ""

        if repo_url:
            github_url = self._clean_github_url(repo_url)
            if github_url:
                result["discovered_urls"]["github_repo"] = github_url

        # Homepage
        homepage = data.get("homepage", "")
        if homepage:
            result["discovered_urls"]["homepage"] = homepage

        # Readme -> raw_content
        readme = data.get("readme", "")
        if readme and readme != "ERROR: No README data found!":
            result["raw_content"] = readme

        # This is a JavaScript/Node.js package
        result["sdk_languages"].append(SourcedFact(
            value="JavaScript",
            source=SourceType.PACKAGE_REGISTRY,
            source_url=source_url,
            confidence=ConfidenceLevel.HIGH,
            raw_evidence=f"Package '{variant}' found on NPM",
        ))
        result["sdk_languages"].append(SourcedFact(
            value="Node.js",
            source=SourceType.PACKAGE_REGISTRY,
            source_url=source_url,
            confidence=ConfidenceLevel.HIGH,
            raw_evidence=f"Package '{variant}' found on NPM",
        ))

        return result

    def _merge_facts(self, existing: dict, new: dict) -> dict:
        """
        Merge new facts into existing result dict, avoiding duplicates.
        """
        # Description: prefer the first found (exact name match comes first in variants)
        if new.get("description") and not existing.get("description"):
            existing["description"] = new["description"]

        # Merge list fields, deduplicating by value
        for field in ("capabilities", "dependencies", "technical_stack", "sdk_languages"):
            existing_values = {f.value for f in existing.get(field, [])}
            for fact in new.get(field, []):
                if fact.value not in existing_values:
                    existing.setdefault(field, []).append(fact)
                    existing_values.add(fact.value)

        # Merge discovered URLs (new values override if not already set)
        for key, url_val in new.get("discovered_urls", {}).items():
            if key not in existing.get("discovered_urls", {}):
                existing.setdefault("discovered_urls", {})[key] = url_val

        # Raw content: concatenate if both exist
        if new.get("raw_content"):
            if existing.get("raw_content"):
                existing["raw_content"] += "\n\n---\n\n" + new["raw_content"]
            else:
                existing["raw_content"] = new["raw_content"]

        return existing

    def discover(self, product_name: str) -> SourceResult:
        """
        Discover product information from PyPI and NPM package registries.

        Args:
            product_name: The product name to search for.

        Returns:
            SourceResult with all discovered facts from package registries.
        """
        logger.info("PackageRegistryDiscovery: searching for '%s'", product_name)

        variants = self._generate_name_variants(product_name)
        logger.debug("Generated %d name variants: %s", len(variants), variants)

        merged = {
            "description": None,
            "capabilities": [],
            "dependencies": [],
            "technical_stack": [],
            "sdk_languages": [],
            "discovered_urls": {},
            "raw_content": None,
        }

        found_anything = False

        for variant in variants:
            # Try PyPI
            pypi_data = self._query_pypi(variant)
            if pypi_data:
                logger.info("Found PyPI package: %s", variant)
                pypi_facts = self._extract_pypi_facts(pypi_data, variant)
                merged = self._merge_facts(merged, pypi_facts)
                found_anything = True

            # Try NPM
            npm_data = self._query_npm(variant)
            if npm_data:
                # NPM can return a result even for non-existent packages in some
                # edge cases; check for a name field to confirm it is real.
                if npm_data.get("name"):
                    logger.info("Found NPM package: %s", variant)
                    npm_facts = self._extract_npm_facts(npm_data, variant)
                    merged = self._merge_facts(merged, npm_facts)
                    found_anything = True

        if not found_anything:
            logger.info("No packages found for '%s' on PyPI or NPM", product_name)
            return SourceResult(
                source_type=SourceType.PACKAGE_REGISTRY,
                success=False,
                error=f"No packages found for '{product_name}' on PyPI or NPM",
                product_name=product_name,
            )

        return SourceResult(
            source_type=SourceType.PACKAGE_REGISTRY,
            success=True,
            product_name=product_name,
            description=merged["description"],
            capabilities=merged["capabilities"],
            dependencies=merged["dependencies"],
            technical_stack=merged["technical_stack"],
            sdk_languages=merged["sdk_languages"],
            discovered_urls=merged["discovered_urls"],
            raw_content=merged["raw_content"],
        )
