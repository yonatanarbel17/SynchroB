"""
Command-line interface for Step 2: Product Generalization
"""

import argparse
import sys
import json
from pathlib import Path
from src.step2 import Step2Generalizer


def load_step1_data(input_file: str) -> dict:
    """Load Step 1 data from JSON or Markdown file."""
    path = Path(input_file)
    
    if not path.exists():
        raise FileNotFoundError(f"Step 1 output file not found: {input_file}")
    
    if path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    elif path.suffix == ".md":
        # For markdown, we'd need to parse it back to JSON
        # For now, raise an error and suggest JSON
        raise ValueError(
            "Markdown files are not yet supported as Step 1 input. "
            "Please use the JSON output from Step 1 (use --format json in step1_cli.py)"
        )
    else:
        # Try to load as JSON anyway
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Step 2: Generalize product from Step 1 output. "
                   "By default, uses intelligent pattern matching (no LLM API calls). "
                   "Use --use-llm to enable LLM-based generalization."
    )
    parser.add_argument(
        "input",
        type=str,
        help="Step 1 output JSON file (from step1_cli.py with --format json)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: auto-generated)"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM APIs (GPT-4 or Gemini) for generalization. Default: Direct intelligent generalization (no API calls)"
    )
    parser.add_argument(
        "--use-gpt4",
        action="store_true",
        help="Use GPT-4 instead of Gemini (only if --use-llm is set). Default: Gemini"
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["markdown", "json"],
        default="markdown",
        help="Output format: markdown or json (default: markdown)"
    )
    
    args = parser.parse_args()
    
    try:
        # Load Step 1 data
        print(f"📂 Loading Step 1 data from: {args.input}")
        step1_data = load_step1_data(args.input)
        
        # Initialize generalizer
        # Default: Direct intelligent generalization (no LLM API calls)
        # Use --use-llm to enable LLM APIs, --use-gpt4 to use GPT-4 instead of Gemini
        use_llm = getattr(args, 'use_llm', False)
        use_gemini = not getattr(args, 'use_gpt4', False) if use_llm else True
        generalizer = Step2Generalizer(use_gemini=use_gemini, use_llm=use_llm)
        
        # Generalize product
        result = generalizer.generalize_product(step1_data)
        
        # Save output
        output_file = generalizer.save_output(result, args.output, format=args.format)
        
        # Print summary
        generalization = result.get("generalization", {})
        functional_dna = generalization.get("functional_dna", {})
        market_reach = generalization.get("market_reach", {})
        friction_report = generalization.get("friction_report", {})
        
        print("\n" + "="*60)
        print("GENERALIZATION SUMMARY")
        print("="*60)
        print(f"\nAbstract Problem: {functional_dna.get('abstract_problem', 'Unknown')}")
        print(f"\nCore Algorithm: {functional_dna.get('core_algorithm', 'Unknown')}")
        print(f"\nUtility Score: {market_reach.get('utility_score', 'N/A')}/10")
        print(f"Market Potential: {market_reach.get('market_potential', 'Unknown')}")
        print(f"\nIntegration Difficulty: {friction_report.get('difficulty', 'Unknown')}")
        print(f"Estimated Hours: {friction_report.get('estimated_hours', 'N/A')}")
        print(f"Risk Level: {friction_report.get('risk_level', 'Unknown')}")
        
        print(f"\n✅ Full generalization saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
