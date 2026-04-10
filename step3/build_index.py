"""
Step 3 — Build Product Index
Reads all batch_results/*.json and produces:
  - product_index.json  (flat searchable records)
  - filter_options.json (unique values per filterable field, for frontend dropdowns)
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

BATCH_DIR = Path(__file__).resolve().parent.parent / "batch_results"
OUTPUT_DIR = Path(__file__).resolve().parent
PRODUCT_INDEX_PATH = OUTPUT_DIR / "product_index.json"
FILTER_OPTIONS_PATH = OUTPUT_DIR / "filter_options.json"


def normalize_tech(raw: str) -> str:
    """Extract clean tech name from strings like 'Python 3.10 (src/backend/)'."""
    # Remove parenthetical path references
    cleaned = re.sub(r"\s*\(.*?\)\s*", "", raw).strip()
    # Remove version numbers for grouping
    # Keep the base name
    cleaned = re.split(r"\s+\d+[\.\d]*", cleaned)[0].strip()
    # Capitalize first letter
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def normalize_language(raw: str) -> str:
    """Extract clean language name from strings like 'Python 3.10 (src/backend/)'."""
    cleaned = re.sub(r"\s*\(.*?\)\s*", "", raw).strip()
    # Take just the language name before version/details
    cleaned = re.split(r"\s+\d+[\.\d]*", cleaned)[0].strip()
    # Handle compound names like "JavaScript/TypeScript"
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def extract_capability_name(cap: Any) -> str:
    """Extract short capability name from various formats."""
    if isinstance(cap, dict):
        return cap.get("name", cap.get("description", str(cap)))
    return str(cap)


def build_product_record(data: dict) -> dict:
    """Extract a flat, searchable record from a full batch result."""
    step1 = data.get("step1", {})
    analysis = step1.get("analysis", {})
    step2 = data.get("step2", {})
    generalization = step2.get("generalization", {})
    functional_dna = generalization.get("functional_dna", {})
    friction = generalization.get("friction_report", {})
    interface_map = generalization.get("interface_map", {})
    deployment = analysis.get("deployment", {})
    project_health = analysis.get("project_health", {})

    # Normalize tech stack
    raw_stack = analysis.get("technical_stack", [])
    tech_stack = sorted(set(normalize_tech(t) for t in raw_stack if t))
    tech_stack = [t for t in tech_stack if len(t) > 1]

    # Normalize languages
    raw_langs = analysis.get("sdk_languages", [])
    sdk_languages = sorted(set(normalize_language(l) for l in raw_langs if l))
    sdk_languages = [l for l in sdk_languages if len(l) > 1]

    # Capabilities as short strings
    raw_caps = analysis.get("capabilities", [])
    capabilities = [extract_capability_name(c) for c in raw_caps]

    # Use cases
    use_cases = analysis.get("use_cases", [])
    if isinstance(use_cases, list):
        use_cases = [str(u) for u in use_cases]

    # Auth methods
    auth_methods = analysis.get("auth_methods", [])
    if isinstance(auth_methods, list):
        auth_methods = [str(a) for a in auth_methods if a]

    # Comparable systems
    comparable = generalization.get("comparable_systems", [])
    if isinstance(comparable, list):
        comparable = [str(c) for c in comparable]

    # Integrations
    integrations = analysis.get("integrations", [])
    if isinstance(integrations, list):
        integrations = [str(i) for i in integrations if i]

    record = {
        "id": data.get("repo_name", "unknown"),
        "product_name": step1.get("product_name", data.get("repo_name", "unknown")),
        "url": data.get("url", ""),
        "category": analysis.get("category", "Unknown"),
        "summary": analysis.get("summary", ""),
        "target_audience": analysis.get("target_audience", ""),
        # Lists for filtering
        "technical_stack": tech_stack,
        "sdk_languages": sdk_languages,
        "capabilities": capabilities,
        "use_cases": use_cases,
        "auth_methods": auth_methods,
        "integrations": integrations,
        # Step 2 — Functional DNA
        "logic_archetype": functional_dna.get("logic_archetype", "Unknown"),
        "abstract_problem": functional_dna.get("abstract_problem", ""),
        "data_flow_pattern": functional_dna.get("data_flow_pattern", ""),
        "state_complexity": functional_dna.get("state_complexity", "Unknown"),
        # Deployment
        "containerized": deployment.get("containerized", False),
        "scaling_model": deployment.get("scaling_model", "Unknown"),
        "ci_cd": deployment.get("ci_cd", ""),
        # Friction / integration effort
        "integration_difficulty": friction.get("difficulty", "Unknown"),
        "estimated_integration_hours": friction.get("estimated_hours", 0),
        "required_technologies": friction.get("required_technologies", []),
        "complexity_factors": friction.get("complexity_factors", []),
        "risk_level": friction.get("risk_level", "Unknown"),
        "migration_path": friction.get("migration_path", ""),
        # Interface
        "api_surface_area": interface_map.get("api_surface_area", "Unknown"),
        "standardization_level": interface_map.get("standardization_level", "Unknown"),
        "adapter_schema": interface_map.get("adapter_schema", {}),
        # Comparable systems
        "comparable_systems": comparable,
        # License
        "license": analysis.get("license", step1.get("extracted_data", {}).get("license", "Unknown")),
        # Project health
        "project_health": {
            "stars": project_health.get("stars", 0),
            "contributors": project_health.get("contributors", 0),
            "last_commit": project_health.get("last_commit", ""),
            "activity_level": project_health.get("activity_level", "Unknown"),
        },
    }

    return record


def build_filter_options(products: list[dict]) -> dict:
    """Compute unique values for each filterable field across all products."""
    categories = set()
    logic_archetypes = set()
    state_complexities = set()
    tech_stack_all = set()
    sdk_languages_all = set()
    auth_methods_all = set()
    integration_difficulties = set()
    risk_levels = set()
    scaling_models = set()
    api_surface_areas = set()
    licenses = set()

    for p in products:
        categories.add(p["category"])
        logic_archetypes.add(p["logic_archetype"])
        state_complexities.add(p["state_complexity"])
        integration_difficulties.add(p["integration_difficulty"])
        risk_levels.add(p["risk_level"])
        scaling_models.add(p["scaling_model"])
        api_surface_areas.add(p["api_surface_area"])
        if p.get("license") and p["license"] != "Unknown":
            licenses.add(p["license"])

        for t in p.get("technical_stack", []):
            tech_stack_all.add(t)
        for l in p.get("sdk_languages", []):
            sdk_languages_all.add(l)
        for a in p.get("auth_methods", []):
            auth_methods_all.add(a)

    return {
        "categories": sorted(categories - {"Unknown"}),
        "logic_archetypes": sorted(logic_archetypes - {"Unknown"}),
        "state_complexities": sorted(state_complexities - {"Unknown"}),
        "technical_stack": sorted(tech_stack_all),
        "sdk_languages": sorted(sdk_languages_all),
        "auth_methods": sorted(auth_methods_all),
        "integration_difficulties": sorted(integration_difficulties - {"Unknown"}),
        "risk_levels": sorted(risk_levels - {"Unknown"}),
        "scaling_models": sorted(scaling_models - {"Unknown"}),
        "api_surface_areas": sorted(api_surface_areas - {"Unknown"}),
        "licenses": sorted(licenses),
        "containerized": [True, False],
    }


def main():
    if not BATCH_DIR.exists():
        print(f"Error: batch_results directory not found at {BATCH_DIR}")
        sys.exit(1)

    products = []
    errors = []

    for fname in sorted(os.listdir(BATCH_DIR)):
        if not fname.endswith(".json") or fname == "batch_results.json":
            continue

        fpath = BATCH_DIR / fname
        try:
            with open(fpath) as f:
                data = json.load(f)

            # Skip failed analyses
            if not data.get("step1", {}).get("analysis"):
                print(f"  SKIP {fname} — no Step 1 analysis")
                continue

            record = build_product_record(data)
            products.append(record)
            cap_count = len(record["capabilities"])
            print(f"  ✓ {record['id']:20s} | {record['category']:45s} | {cap_count} caps")

        except Exception as e:
            errors.append((fname, str(e)))
            print(f"  ✗ {fname} — {e}")

    # Build filter options
    filter_options = build_filter_options(products)

    # Write outputs
    with open(PRODUCT_INDEX_PATH, "w") as f:
        json.dump(products, f, indent=2)

    with open(FILTER_OPTIONS_PATH, "w") as f:
        json.dump(filter_options, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Indexed {len(products)} products → {PRODUCT_INDEX_PATH.name}")
    print(f"Filter options ({sum(len(v) for v in filter_options.values())} unique values) → {FILTER_OPTIONS_PATH.name}")
    if errors:
        print(f"\n{len(errors)} errors:")
        for fname, err in errors:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
