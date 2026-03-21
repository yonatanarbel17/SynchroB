#!/usr/bin/env python3
"""
Batch analysis of GitHub repositories using SynchroB.

Reads a text file of GitHub repo URLs (one per line), clones each repo,
runs local source code analysis via the repo-analyzer skill, then pipes
the result through Step 1 (Product Analysis) and Step 2 (Generalization).

Usage:
    python batch_analyze.py repos.txt [--output results/] [--keep-clones] [--use-gemini] [--use-openai]

The input file should contain one GitHub URL per line. Lines starting with
# are treated as comments. Blank lines are ignored.

Example repos.txt:
    # Payment processors
    https://github.com/stripe/stripe-python.git
    https://github.com/paypal/PayPal-Python-SDK.git

    # Auth libraries
    https://github.com/jpadilla/pyjwt.git
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config
from src.analysis import ClaudeClient, GeminiClient, OpenAIClient
from src.discovery.local_repo_discovery import LocalRepoDiscovery
from src.discovery.merger import SourceMerger
from src.step1.processor import Step1Processor
from src.step2.generalizer import Step2Generalizer
from src.utils import setup_logger

logger = setup_logger("batch_analyze")


def parse_url_file(filepath: str) -> List[str]:
    """
    Read a text file and extract GitHub URLs.

    Skips blank lines and lines starting with #.
    """
    urls = []
    with open(filepath, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Basic validation
            if "github.com" not in line and "gitlab.com" not in line:
                logger.warning(
                    "Line %d: '%s' doesn't look like a GitHub URL — skipping",
                    line_num,
                    line[:80],
                )
                continue
            urls.append(line)
    return urls


def analyze_single_repo(
    github_url: str,
    local_discovery: LocalRepoDiscovery,
    step1_processor: Step1Processor,
    step2_generalizer: Step2Generalizer,
    keep_clone: bool = False,
) -> Dict[str, Any]:
    """
    Run the full SynchroB pipeline on a single GitHub repo.

    1. Clone + extract + LLM analyze via LocalRepoDiscovery
    2. Convert SourceResult → Step 1 compatible dict
    3. Run Step 2 generalization

    Returns a dict with keys: url, repo_name, step1, step2, errors
    """
    result = {
        "url": github_url,
        "repo_name": github_url.rstrip("/").split("/")[-1].replace(".git", ""),
        "timestamp": datetime.now().isoformat(),
        "step1": None,
        "step2": None,
        "errors": [],
    }

    # --- Step 0: Local repo discovery (clone + extract + LLM) ---
    logger.info("=== Analyzing %s ===", github_url)
    source_result = local_discovery.discover(github_url, keep_clone=keep_clone)

    if not source_result.success:
        error_msg = f"Local repo discovery failed: {source_result.error}"
        logger.error(error_msg)
        result["errors"].append(error_msg)
        return result

    # --- Build Step 1 compatible data from SourceResult ---
    # The Step 1 processor normally produces this dict from web scraping.
    # We construct an equivalent from our local analysis so Step 2 can consume it.
    step1_data = _source_result_to_step1_dict(source_result)
    result["step1"] = step1_data

    # --- Step 2: Generalization ---
    try:
        step2_data = step2_generalizer.generalize_product(step1_data)
        result["step2"] = step2_data
    except Exception as exc:
        error_msg = f"Step 2 generalization failed: {exc}"
        logger.error(error_msg)
        result["errors"].append(error_msg)

    return result


def _source_result_to_step1_dict(source_result) -> Dict[str, Any]:
    """
    Convert a SourceResult (from local repo analysis) into the dict format
    that Step 2 expects as Step 1 output.

    This bridges the gap between the new discovery pipeline's data model
    and the existing Step 1 → Step 2 interface.
    """
    analysis = {
        "summary": source_result.description or "",
        "capabilities": [f.value for f in source_result.capabilities],
        "use_cases": [],
        "technical_stack": [f.value for f in source_result.technical_stack],
        "integrations": [f.value for f in source_result.integrations],
        "api_endpoints": [
            {
                "method": ep.method,
                "path": ep.path,
                "summary": ep.summary,
            }
            for ep in source_result.api_endpoints
        ],
        "pricing": {"model": "open-source", "free_tier": "true"},
        "target_audience": "Developers",
        "category": "Open Source Software",
        "deployment": "Self-hosted",
        "underlying_algorithm": {
            "problem_type": "",
            "pattern": "",
        },
        "evidence_tracking": {
            "confidence_level": "High",
            "technical_facts": [f.value for f in source_result.capabilities[:10]],
            "information_gaps": [],
        },
        "architecture_patterns": [f.value for f in source_result.architecture_patterns],
        "auth_methods": [f.value for f in source_result.auth_methods],
        "sdk_languages": [f.value for f in source_result.sdk_languages],
        "dependencies": [f.value for f in source_result.dependencies],
        "deployment_options": [f.value for f in source_result.deployment_options],
    }

    return {
        "product_name": source_result.product_name or "",
        "url": source_result.product_url or "",
        "analysis": analysis,
        "extracted_data": {},
        "source": "local_repo",
        "source_confidence": "high",
        "timestamp": datetime.now().isoformat(),
    }


def run_batch(
    url_file: str,
    output_dir: str,
    keep_clones: bool = False,
    use_gemini: bool = True,
    use_llm: bool = True,
) -> List[Dict[str, Any]]:
    """
    Run the batch analysis pipeline.

    Args:
        url_file: Path to text file with GitHub URLs
        output_dir: Directory for results (created if needed)
        keep_clones: If True, don't delete cloned repos
        use_gemini: Use Gemini API (default True, cheaper)
        use_llm: Use LLM for Step 1/2 strategies

    Returns:
        List of result dicts, one per repo
    """
    # Parse URLs
    urls = parse_url_file(url_file)
    if not urls:
        logger.error("No valid URLs found in %s", url_file)
        return []
    logger.info("Found %d repos to analyze", len(urls))

    # Validate config
    config.validate(multi_source=True)

    # Initialize clients — Claude is the go-to / default
    claude_client = None
    gemini_client = None
    openai_client = None

    if config.ANTHROPIC_API_KEY:
        try:
            claude_client = ClaudeClient()
            logger.info("Using Claude (Anthropic) for LLM analysis — default")
        except Exception as exc:
            logger.warning("Could not initialize Claude: %s", exc)

    if not claude_client and use_gemini and config.GEMINI_API_KEY:
        try:
            gemini_client = GeminiClient()
            logger.info("Using Gemini for LLM analysis (fallback)")
        except Exception as exc:
            logger.warning("Could not initialize Gemini: %s", exc)

    if not claude_client and not gemini_client and config.OPENAI_API_KEY:
        try:
            openai_client = OpenAIClient()
            logger.info("Using OpenAI for LLM analysis (fallback)")
        except Exception as exc:
            logger.warning("Could not initialize OpenAI: %s", exc)

    if not claude_client and not gemini_client and not openai_client:
        logger.error("No LLM client available. Set ANTHROPIC_API_KEY (preferred), GEMINI_API_KEY, or OPENAI_API_KEY.")
        return []

    # Initialize pipeline components
    local_discovery = LocalRepoDiscovery(
        claude_client=claude_client,
        gemini_client=gemini_client,
        openai_client=openai_client,
    )
    step1_processor = Step1Processor(use_gemini=use_gemini, use_llm=use_llm)
    step2_generalizer = Step2Generalizer(use_gemini=use_gemini, use_llm=use_llm)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Process each repo (with rate-limit delay between requests)
    results = []
    for i, url in enumerate(urls, 1):
        # Rate-limit delay — avoid 429 errors on API tiers with low token/min limits
        if i > 1:
            logger.info("Waiting 70s between repos to respect API rate limits...")
            time.sleep(70)

        logger.info("--- Repo %d/%d ---", i, len(urls))
        try:
            result = analyze_single_repo(
                github_url=url,
                local_discovery=local_discovery,
                step1_processor=step1_processor,
                step2_generalizer=step2_generalizer,
                keep_clone=keep_clones,
            )
            results.append(result)

            # Save individual result
            repo_name = result["repo_name"]
            individual_path = os.path.join(output_dir, f"{repo_name}.json")
            with open(individual_path, "w") as f:
                json.dump(result, f, indent=2, default=str)
            logger.info("Saved result to %s", individual_path)

        except Exception as exc:
            logger.exception("Fatal error processing %s", url)
            results.append({
                "url": url,
                "repo_name": url.rstrip("/").split("/")[-1].replace(".git", ""),
                "timestamp": datetime.now().isoformat(),
                "step1": None,
                "step2": None,
                "errors": [str(exc)],
            })

    # Save combined results
    combined_path = os.path.join(output_dir, "batch_results.json")
    with open(combined_path, "w") as f:
        json.dump(
            {
                "batch_timestamp": datetime.now().isoformat(),
                "total_repos": len(urls),
                "successful": sum(1 for r in results if not r.get("errors")),
                "failed": sum(1 for r in results if r.get("errors")),
                "results": results,
            },
            f,
            indent=2,
            default=str,
        )
    logger.info("Saved combined results to %s", combined_path)

    # Summary
    success = sum(1 for r in results if not r.get("errors"))
    failed = len(results) - success
    logger.info(
        "=== Batch complete: %d/%d succeeded, %d failed ===",
        success,
        len(results),
        failed,
    )

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Batch analyze GitHub repos through the SynchroB pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python batch_analyze.py repos.txt --output results/
    python batch_analyze.py repos.txt --keep-clones --output /tmp/analysis/
        """,
    )
    parser.add_argument(
        "url_file",
        help="Text file with GitHub URLs (one per line, # for comments)",
    )
    parser.add_argument(
        "--output", "-o",
        default="batch_results",
        help="Output directory for results (default: batch_results/)",
    )
    parser.add_argument(
        "--keep-clones",
        action="store_true",
        help="Don't delete cloned repos after analysis",
    )
    parser.add_argument(
        "--use-openai",
        action="store_true",
        help="Use OpenAI instead of Gemini for LLM analysis",
    )
    parser.add_argument(
        "--no-llm-steps",
        action="store_true",
        help="Use direct analysis for Steps 1 & 2 (skip LLM for generalization)",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.url_file):
        print(f"Error: URL file not found: {args.url_file}", file=sys.stderr)
        return 1

    results = run_batch(
        url_file=args.url_file,
        output_dir=args.output,
        keep_clones=args.keep_clones,
        use_gemini=not args.use_openai,
        use_llm=not args.no_llm_steps,
    )

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
