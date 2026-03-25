"""
Local repository discovery source.

Clones a Git repo, runs the deterministic extraction script, then sends
the structured extraction to an LLM guided by the repo-analyzer SKILL.md
for deep technical analysis. Results get HIGH confidence because they come
from actual source code, not marketing pages.

This is the most authoritative source after OpenAPI specs (weight 90).
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from src.utils import parse_llm_json_response
from src.discovery.models import (
    SourceType,
    ConfidenceLevel,
    SourcedFact,
    SourcedEndpoint,
    SourceResult,
)

logger = logging.getLogger(__name__)

# Path to the extraction script and skill, relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXTRACTION_SCRIPT = _PROJECT_ROOT / "skills" / "repo-analyzer" / "scripts" / "extract_repo_structure.py"
SKILL_PATH = _PROJECT_ROOT / "skills" / "repo-analyzer" / "SKILL.md"


class LocalRepoDiscovery:
    """
    Analyze a repository by cloning it locally, running deterministic extraction,
    and sending the structured data to an LLM using the repo-analyzer skill.
    """

    def __init__(self, claude_client=None, gemini_client=None, openai_client=None):
        self.claude_client = claude_client  # Default / go-to
        self.gemini_client = gemini_client
        self.openai_client = openai_client
        self._skill_instructions: Optional[str] = None

    def discover(
        self,
        github_url: str,
        keep_clone: bool = False,
        local_path: Optional[str] = None,
    ) -> SourceResult:
        """
        Run full local repo analysis pipeline.

        1. Clone the repo (or use local_path if given)
        2. Run extract_repo_structure.py to get structured JSON
        3. Load the repo-analyzer SKILL.md
        4. Send extraction + skill instructions to the LLM
        5. Parse the LLM response into a SourceResult

        Args:
            github_url: URL of the GitHub repo to clone
            keep_clone: If True, don't clean up the cloned directory
            local_path: If provided, skip cloning and use this local path

        Returns:
            SourceResult with source_type=LOCAL_REPO
        """
        clone_dir = None
        repo_path = local_path

        try:
            # Step 1: Clone (if needed)
            if not repo_path:
                repo_path, clone_dir = self._clone_repo(github_url)
                logger.info("Cloned %s to %s", github_url, repo_path)

            # Step 2: Run extraction script
            extraction = self._run_extraction(repo_path)
            if extraction is None:
                return SourceResult(
                    source_type=SourceType.LOCAL_REPO,
                    success=False,
                    error="Extraction script failed to produce output",
                    product_url=github_url,
                )
            logger.info(
                "Extraction complete: %d files, %d source samples",
                extraction.get("total_files", 0),
                len(extraction.get("source_samples", {})),
            )

            # Step 3: Load skill instructions
            skill_instructions = self._load_skill()

            # Step 4: Query LLM with extraction + skill
            llm_response = self._query_llm(extraction, skill_instructions, github_url)
            if llm_response is None:
                return SourceResult(
                    source_type=SourceType.LOCAL_REPO,
                    success=False,
                    error="LLM analysis failed — no response from any client",
                    product_url=github_url,
                )

            # Step 5: Parse into SourceResult
            try:
                data = parse_llm_json_response(llm_response)
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("Failed to parse LLM repo analysis as JSON: %s", exc)
                return SourceResult(
                    source_type=SourceType.LOCAL_REPO,
                    success=False,
                    error=f"JSON parse error: {exc}",
                    product_url=github_url,
                    raw_content=llm_response[:2000],
                )

            source_result = self._build_source_result(data, github_url, extraction)
            # Store the raw LLM analysis JSON so downstream can use the full
            # rich output without lossy SourceResult conversion
            source_result.raw_llm_analysis = data
            return source_result

        except Exception as exc:
            logger.exception("LocalRepoDiscovery failed for %s", github_url)
            return SourceResult(
                source_type=SourceType.LOCAL_REPO,
                success=False,
                error=str(exc),
                product_url=github_url,
            )
        finally:
            # Cleanup clone unless keep_clone is True
            if clone_dir and not keep_clone:
                shutil.rmtree(clone_dir, ignore_errors=True)
                logger.info("Cleaned up clone directory %s", clone_dir)

    # ------------------------------------------------------------------
    # Step 1: Clone
    # ------------------------------------------------------------------

    @staticmethod
    def _clone_repo(github_url: str) -> Tuple[str, str]:
        """
        Shallow-clone a repo into a temp directory.

        Returns:
            (repo_path, parent_tmpdir) — caller is responsible for cleanup
        """
        tmpdir = tempfile.mkdtemp(prefix="synchrob_local_")
        repo_name = github_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_path = os.path.join(tmpdir, repo_name)

        subprocess.run(
            ["git", "clone", "--depth", "1", github_url, repo_path],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return repo_path, tmpdir

    # ------------------------------------------------------------------
    # Step 2: Run extraction
    # ------------------------------------------------------------------

    def _run_extraction(self, repo_path: str) -> Optional[Dict[str, Any]]:
        """
        Run extract_repo_structure.py as a subprocess and parse its JSON output.
        Falls back to in-process import if subprocess fails.
        """
        if not EXTRACTION_SCRIPT.exists():
            logger.error("Extraction script not found at %s", EXTRACTION_SCRIPT)
            return None

        try:
            result = subprocess.run(
                [sys.executable, str(EXTRACTION_SCRIPT), repo_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.warning(
                    "Extraction script exited with code %d: %s",
                    result.returncode,
                    result.stderr[:500],
                )
                return None

            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            logger.warning("Extraction script timed out for %s", repo_path)
            return None
        except json.JSONDecodeError as exc:
            logger.warning("Extraction script produced invalid JSON: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Step 3: Load skill
    # ------------------------------------------------------------------

    def _load_skill(self) -> str:
        """Load and cache the repo-analyzer SKILL.md instructions."""
        if self._skill_instructions is not None:
            return self._skill_instructions

        if not SKILL_PATH.exists():
            logger.warning("SKILL.md not found at %s, using minimal prompt", SKILL_PATH)
            self._skill_instructions = (
                "Analyze this repository extraction and produce a JSON object describing "
                "its architecture, capabilities, tech stack, and API endpoints."
            )
            return self._skill_instructions

        raw = SKILL_PATH.read_text(encoding="utf-8")

        # Strip YAML frontmatter (everything between the first two ---  lines)
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                raw = parts[2]

        self._skill_instructions = raw.strip()
        return self._skill_instructions

    # ------------------------------------------------------------------
    # Step 4: Query LLM
    # ------------------------------------------------------------------

    def _query_llm(
        self,
        extraction: Dict[str, Any],
        skill_instructions: str,
        github_url: str,
    ) -> Optional[str]:
        """
        Send the repo extraction to an LLM along with the skill instructions.
        Tries Gemini first (cheaper), then falls back to OpenAI.
        """
        # Build the extraction summary — truncate to avoid token limits
        extraction_text = self._format_extraction_for_llm(extraction)

        prompt = f"""{skill_instructions}

---

## Repository: {extraction.get('repo_name', github_url)}
GitHub URL: {github_url}

## Extraction Data

{extraction_text}

---

Respond ONLY with valid JSON matching the schema described above. No additional text."""

        # Try Claude first (default / go-to)
        if self.claude_client:
            response = self._query_claude(prompt)
            if response:
                return response

        # Fall back to Gemini
        if self.gemini_client:
            response = self._query_gemini(prompt)
            if response:
                return response

        # Fall back to OpenAI
        if self.openai_client:
            response = self._query_openai(prompt)
            if response:
                return response

        return None

    def _query_claude(self, prompt: str) -> Optional[str]:
        """Query Claude (Anthropic) and return raw text. Default / go-to LLM."""
        try:
            return self.claude_client.generate(
                prompt,
                system=(
                    "You are a Technical Repository Analyzer producing comprehensive, "
                    "detailed JSON analyses. Fill every field thoroughly. "
                    "Aim for 15-25 capabilities with file evidence. "
                    "Respond only with valid JSON."
                ),
                max_tokens=8192,
            )
        except Exception as exc:
            logger.warning("Claude query failed for repo analysis: %s", exc)
            return None

    def _query_gemini(self, prompt: str) -> Optional[str]:
        """Query Gemini and return raw text."""
        try:
            response = self.gemini_client.client.models.generate_content(
                model=self.gemini_client.model_name,
                contents=prompt,
            )
            if hasattr(response, "text"):
                return response.text.strip()
            if hasattr(response, "candidates") and response.candidates:
                return response.candidates[0].content.parts[0].text.strip()
            return str(response)
        except Exception as exc:
            logger.warning("Gemini query failed for repo analysis: %s", exc)
            return None

    def _query_openai(self, prompt: str) -> Optional[str]:
        """Query OpenAI and return raw text."""
        try:
            response = self.openai_client.client.chat.completions.create(
                model=self.openai_client.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Technical Repository Analyzer. "
                            "Respond only with valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.warning("OpenAI query failed for repo analysis: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Extraction formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_extraction_for_llm(extraction: Dict[str, Any]) -> str:
        """
        Format the extraction dict into a readable text block for the LLM.

        Budget allocation (total ~60k chars):
          - Directory structure + file tree:  4k
          - Language distribution:             500
          - README:                           6k
          - Architecture/design docs:         6k
          - Dependencies:                     4k
          - OpenAPI specs:                    5k
          - Config files:                     3k
          - DB schemas:                       3k
          - Source code samples:             20k  (the most important section)
          - Test info:                        1k
          - Git metadata:                     2k
          - Plugin system:                    1k
          - License + community health:       500
          - Buffer:                           4k
        """
        parts = []

        # --- 1. Directory structure (3-level tree) ---
        dir_structure = extraction.get("directory_structure")
        if dir_structure:
            parts.append("### Directory Structure (3-level)")
            if isinstance(dir_structure, dict):
                tree_str = json.dumps(dir_structure.get("directory_tree", dir_structure), indent=1)
                parts.append(tree_str[:2000])
            else:
                parts.append(str(dir_structure)[:2000])

        # --- 2. File tree ---
        file_tree = extraction.get("file_tree", [])
        parts.append(f"\n### File Tree ({len(file_tree)} files total)")
        max_tree = min(300, len(file_tree))
        parts.append("\n".join(file_tree[:max_tree]))
        if len(file_tree) > max_tree:
            parts.append(f"... and {len(file_tree) - max_tree} more files")

        # --- 3. Language distribution ---
        lang_dist = extraction.get("language_distribution", {})
        if lang_dist:
            parts.append("\n### Language Distribution")
            for ext, count in lang_dist.items():
                parts.append(f"  {ext}: {count} files")

        # --- 4. README ---
        readme = extraction.get("readme")
        if readme:
            parts.append("\n### README")
            parts.append(readme[:6000])

        # --- 5. Architecture / design docs ---
        docs = extraction.get("docs", {})
        if docs:
            parts.append("\n### Architecture & Design Documentation")
            doc_budget = 6000
            for fpath, content in docs.items():
                if doc_budget <= 0:
                    break
                chunk = content[:min(3000, doc_budget)]
                parts.append(f"\n**{fpath}**:")
                parts.append(chunk)
                doc_budget -= len(chunk)

        # --- 6. Dependencies ---
        deps = extraction.get("dependencies", {})
        if deps:
            parts.append("\n### Dependency Manifests")
            dep_budget = 4000
            for fpath, dep_info in deps.items():
                if dep_budget <= 0:
                    break
                parts.append(f"\n**{fpath}** ({dep_info.get('ecosystem', 'unknown')}):")
                parsed = dep_info.get("parsed")
                if parsed:
                    chunk = json.dumps(parsed, indent=2)[:min(2000, dep_budget)]
                else:
                    chunk = dep_info.get("raw", "")[:min(1500, dep_budget)]
                parts.append(chunk)
                dep_budget -= len(chunk)

        # --- 7. OpenAPI specs ---
        specs = extraction.get("openapi_specs", {})
        if specs:
            parts.append("\n### OpenAPI/Swagger Specs Found on Disk")
            for fpath, spec_info in specs.items():
                parts.append(f"\n**{fpath}**:")
                parsed = spec_info.get("parsed")
                if parsed:
                    parts.append(json.dumps(parsed, indent=2)[:5000])
                else:
                    parts.append(spec_info.get("raw", "")[:3000])

        # --- 8. Database schemas ---
        db_schemas = extraction.get("db_schemas", {})
        if db_schemas:
            migrations = db_schemas.get("migration_files", [])
            models = db_schemas.get("orm_models", [])
            samples = db_schemas.get("samples", {})
            if migrations or models or samples:
                parts.append("\n### Database Schemas & Migrations")
                if migrations:
                    parts.append(f"Migration files found: {len(migrations)}")
                    parts.append(", ".join(migrations[:10]))
                if models:
                    parts.append(f"ORM model files: {len(models)}")
                    parts.append(", ".join(models[:10]))
                for fpath, content in samples.items():
                    parts.append(f"\n**{fpath}**:")
                    parts.append(f"```\n{content}\n```")

        # --- 9. Config files ---
        configs = extraction.get("config_files", {})
        if configs:
            parts.append("\n### Configuration Files")
            config_budget = 3000
            for fpath, content in configs.items():
                if config_budget <= 0:
                    break
                chunk = content[:min(1500, config_budget)]
                parts.append(f"\n**{fpath}**:")
                parts.append(chunk)
                config_budget -= len(chunk)

        # --- 10. Source code samples (LARGEST BUDGET — most important) ---
        source_samples = extraction.get("source_samples", {})
        if source_samples:
            parts.append(f"\n### Source Code Samples ({len(source_samples)} files)")
            source_budget = 20000
            for fpath, content in source_samples.items():
                if source_budget <= 0:
                    break
                chunk = content[:min(4000, source_budget)]
                parts.append(f"\n**{fpath}**:")
                parts.append(f"```\n{chunk}\n```")
                source_budget -= len(chunk)

        # --- 11. Test info ---
        test_info = extraction.get("test_info", {})
        if test_info:
            parts.append("\n### Test Infrastructure")
            parts.append(f"Test files: {test_info.get('test_file_count', 0)}")
            frameworks = test_info.get("frameworks", [])
            if frameworks:
                parts.append(f"Test frameworks: {', '.join(frameworks)}")
            sample_paths = test_info.get("sample_paths", [])
            if sample_paths:
                parts.append(f"Sample test files: {', '.join(sample_paths[:5])}")

        # --- 12. Git metadata ---
        git_meta = extraction.get("git_metadata", {})
        if git_meta:
            parts.append("\n### Git Metadata")
            if git_meta.get("total_commits"):
                parts.append(f"Total commits: {git_meta['total_commits']}")
            if git_meta.get("created_date"):
                parts.append(f"Repository created: {git_meta['created_date']}")
            contributors = git_meta.get("top_contributors", [])
            if contributors:
                parts.append(f"Top contributors ({len(contributors)}):")
                for c in contributors[:10]:
                    parts.append(f"  {c}")
            recent = git_meta.get("recent_commits", [])
            if recent:
                parts.append(f"Recent commits ({len(recent)}):")
                for c in recent[:15]:
                    parts.append(f"  {c}")

        # --- 13. Plugin system ---
        plugin_sys = extraction.get("plugin_system", {})
        if plugin_sys and plugin_sys.get("has_plugin_system"):
            parts.append("\n### Plugin/Extension System")
            plugin_dirs = plugin_sys.get("plugin_directories", [])
            if plugin_dirs:
                parts.append(f"Plugin directories: {', '.join(plugin_dirs[:10])}")
            patterns = plugin_sys.get("hook_patterns", [])
            if patterns:
                parts.append(f"Hook/event patterns: {', '.join(patterns[:5])}")

        # --- 14. License & community health ---
        license_info = extraction.get("license")
        if license_info:
            parts.append(f"\n### License: {license_info}")

        community = extraction.get("community_health", {})
        if community:
            present = [k for k, v in community.items() if v]
            if present:
                parts.append(f"\n### Community Health: {', '.join(present)}")

        result = "\n".join(parts)
        # Hard cap at 60k chars — well within Claude's context window
        if len(result) > 60000:
            result = result[:60000] + "\n\n... [truncated to fit token limit]"
        return result

    # ------------------------------------------------------------------
    # Step 5: Build SourceResult
    # ------------------------------------------------------------------

    def _build_source_result(
        self,
        data: Dict[str, Any],
        github_url: str,
        extraction: Dict[str, Any],
    ) -> SourceResult:
        """Convert parsed LLM analysis JSON into a SourceResult."""
        src = SourceType.LOCAL_REPO
        conf = ConfidenceLevel.HIGH  # Source code analysis = high confidence

        result = SourceResult(
            source_type=src,
            success=True,
            product_name=extraction.get("repo_name", ""),
            product_url=github_url,
            description=data.get("summary"),
        )

        # Capabilities
        for cap in data.get("capabilities", []):
            if cap and isinstance(cap, str) and len(cap.strip()) > 3:
                result.capabilities.append(
                    SourcedFact(
                        value=cap.strip(),
                        source=src,
                        source_url=github_url,
                        confidence=conf,
                    )
                )

        # API endpoints
        for ep_str in data.get("api_endpoints", []):
            if not ep_str or not isinstance(ep_str, str):
                continue
            # Expected format: "METHOD /path — description (source)"
            parts = ep_str.strip().split(" ", 1)
            if len(parts) == 2 and parts[0].upper() in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                method = parts[0].upper()
                path_and_rest = parts[1]
                # Extract just the path before any dash or description
                path = path_and_rest.split("—")[0].split(" - ")[0].strip()
                summary = path_and_rest[len(path):].strip(" —-")
            else:
                method = None
                path = ep_str.strip()
                summary = None

            result.api_endpoints.append(
                SourcedEndpoint(
                    method=method,
                    path=path,
                    summary=summary or None,
                    source=src,
                    source_url=github_url,
                    confidence=conf,
                )
            )

        # Auth methods
        for auth in data.get("auth_methods", []):
            if auth and isinstance(auth, str):
                result.auth_methods.append(
                    SourcedFact(value=auth.strip(), source=src, source_url=github_url, confidence=conf)
                )

        # SDK languages
        for lang in data.get("sdk_languages", []):
            if lang and isinstance(lang, str):
                result.sdk_languages.append(
                    SourcedFact(value=lang.strip(), source=src, source_url=github_url, confidence=conf)
                )

        # Integrations
        for integ in data.get("integrations", []):
            if integ and isinstance(integ, str):
                result.integrations.append(
                    SourcedFact(value=integ.strip(), source=src, source_url=github_url, confidence=conf)
                )

        # Technical stack
        for tech in data.get("technical_stack", []):
            if tech and isinstance(tech, str):
                result.technical_stack.append(
                    SourcedFact(value=tech.strip(), source=src, source_url=github_url, confidence=conf)
                )

        # Architecture patterns
        arch = data.get("architecture", {})
        if isinstance(arch, dict):
            pattern = arch.get("pattern", "")
            if pattern:
                result.architecture_patterns.append(
                    SourcedFact(value=pattern, source=src, source_url=github_url, confidence=conf)
                )
            concurrency = arch.get("concurrency_model", "")
            if concurrency:
                result.architecture_patterns.append(
                    SourcedFact(
                        value=f"Concurrency: {concurrency}",
                        source=src,
                        source_url=github_url,
                        confidence=conf,
                    )
                )

        # Deployment info
        deploy = data.get("deployment", {})
        if isinstance(deploy, dict):
            if deploy.get("containerized"):
                result.deployment_options.append(
                    SourcedFact(value="Containerized (Docker)", source=src, source_url=github_url, confidence=conf)
                )
            ci = deploy.get("ci_cd", "")
            if ci and ci.lower() != "none observed":
                result.deployment_options.append(
                    SourcedFact(value=f"CI/CD: {ci}", source=src, source_url=github_url, confidence=conf)
                )

        # Dependencies as SourcedFacts
        dep_data = data.get("dependencies", {})
        if isinstance(dep_data, dict):
            for dep in dep_data.get("runtime", []):
                if dep and isinstance(dep, str):
                    result.dependencies.append(
                        SourcedFact(value=dep.strip(), source=src, source_url=github_url, confidence=conf)
                    )
            for dep in dep_data.get("infrastructure", []):
                if dep and isinstance(dep, str):
                    result.dependencies.append(
                        SourcedFact(
                            value=f"Infrastructure: {dep.strip()}",
                            source=src,
                            source_url=github_url,
                            confidence=conf,
                        )
                    )

        # Discovered URLs
        result.discovered_urls["github_repo"] = github_url

        # Build raw content for downstream Step 1/Step 2
        raw_parts = [f"# {result.product_name} (Local Repo Analysis)\n"]
        if data.get("summary"):
            raw_parts.append(data["summary"])
        if data.get("capabilities"):
            raw_parts.append("\n## Capabilities")
            raw_parts.extend(f"- {c}" for c in data["capabilities"])
        if data.get("api_endpoints"):
            raw_parts.append("\n## API Endpoints")
            raw_parts.extend(f"- {e}" for e in data["api_endpoints"])
        result.raw_content = "\n".join(raw_parts)

        logger.info(
            "Local repo analysis: %d capabilities, %d endpoints, %d tech stack items",
            len(result.capabilities),
            len(result.api_endpoints),
            len(result.technical_stack),
        )

        return result
