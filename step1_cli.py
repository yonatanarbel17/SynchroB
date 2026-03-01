"""
Command-line interface for Step 1: Product Analysis
"""

import argparse
import sys
from src.step1 import Step1Processor


def main():
    parser = argparse.ArgumentParser(
        description="Step 1: Analyze a product page and extract functional information. "
                   "By default, uses intelligent pattern matching (no LLM API calls). "
                   "Use --use-llm to enable LLM-based analysis."
    )
    parser.add_argument(
        "url",
        type=str,
        help="Product main page URL to analyze"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output JSON file path (default: auto-generated)"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM APIs (GPT-4 or Gemini) for analysis. Default: Direct intelligent analysis (no API calls)"
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
    parser.add_argument(
        "--crawl-depth",
        type=int,
        default=0,
        help="Depth to crawl linked pages (0 = main page only)"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize processor
        # Default: Direct intelligent analysis (no LLM API calls)
        # Use --use-llm to enable LLM APIs, --use-gpt4 to use GPT-4 instead of Gemini
        use_llm = getattr(args, 'use_llm', False)
        use_gemini = not getattr(args, 'use_gpt4', False) if use_llm else True
        processor = Step1Processor(use_gemini=use_gemini, use_llm=use_llm)
        
        # Analyze product
        result = processor.analyze_product(args.url, crawl_depth=args.crawl_depth)
        
        # Save output
        output_file = processor.save_output(result, args.output, format=args.format)
        
        # Print summary
        print("\n" + "="*60)
        print("ANALYSIS SUMMARY")
        print("="*60)
        print(f"Product: {result['extracted_data'].get('title', 'Unknown')}")
        print(f"\nSummary: {result['analysis'].get('summary', 'N/A')}")
        print(f"\nCategory: {result['analysis'].get('category', 'Unknown')}")
        print(f"\nCapabilities ({len(result['analysis'].get('capabilities', []))}):")
        for cap in result['analysis'].get('capabilities', [])[:5]:
            print(f"  • {cap}")
        if len(result['analysis'].get('capabilities', [])) > 5:
            print(f"  ... and {len(result['analysis'].get('capabilities', [])) - 5} more")
        
        print(f"\n✅ Full analysis saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
