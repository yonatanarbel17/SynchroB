"""
Command-line interface for Step 1: Product Analysis

Usage:
    # Multi-source discovery (recommended):
    python step1_cli.py stripe
    python step1_cli.py stripe --url https://stripe.com
    python step1_cli.py "twilio" --use-llm

    # Cursor mode (skip external LLMs — outputs raw data for Cursor to analyze):
    python step1_cli.py stripe --cursor

    # Legacy single-source (URL-only):
    python step1_cli.py https://www.etoro.com --url-only
    python step1_cli.py https://stripe.com --url-only --crawl-depth 2
"""

import argparse
import sys
from src.step1 import Step1Processor


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Step 1: Analyze a product and extract functional information. "
            "Provide a product name for multi-source discovery (recommended), "
            "or a URL with --url-only for legacy single-source analysis."
        )
    )
    parser.add_argument(
        "product",
        type=str,
        help=(
            "Product name (e.g. 'stripe', 'twilio') for multi-source discovery, "
            "or a URL when used with --url-only"
        ),
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Product URL (optional). Helps discovery find OpenAPI specs and docs.",
    )
    parser.add_argument(
        "--url-only",
        action="store_true",
        help="Legacy mode: treat the product argument as a URL and use single-source web scraping only.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: auto-generated in outputs/)",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM APIs (Gemini or GPT-4) for the analysis strategy. "
             "Note: multi-source mode always uses LLM for the knowledge discovery phase.",
    )
    parser.add_argument(
        "--use-gpt4",
        action="store_true",
        help="Use GPT-4 instead of Gemini for the analysis strategy.",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["markdown", "json"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--crawl-depth",
        type=int,
        default=1,
        help="Depth to crawl linked pages (default: 1)",
    )
    parser.add_argument(
        "--cursor",
        action="store_true",
        help=(
            "Cursor mode: skip external LLM APIs entirely. "
            "Runs non-LLM discovery sources (package registries, OpenAPI, GitHub, web scrape) "
            "and outputs raw structured data for Cursor's own LLM to analyze."
        ),
    )

    args = parser.parse_args()

    try:
        # Determine mode
        product_arg = args.product
        is_url = product_arg.startswith("http://") or product_arg.startswith("https://")

        # Initialize processor
        use_llm = args.use_llm and not args.cursor  # Cursor mode skips external LLMs
        use_gemini = not args.use_gpt4 if use_llm else True
        processor = Step1Processor(use_gemini=use_gemini, use_llm=use_llm)

        if args.url_only or (is_url and not args.url):
            # ── Legacy single-source mode ────────────────────────────
            url = product_arg
            print(f"📡 Running single-source analysis on {url}")
            result = processor.analyze_product(url, crawl_depth=args.crawl_depth)
        elif args.cursor:
            # ── Cursor mode (no external LLM calls) ─────────────────
            product_name = product_arg
            product_url = args.url if args.url else (product_arg if is_url else None)
            print(f"📡 Cursor mode: discovery-only for '{product_name}'")
            print("   (Skipping external LLM APIs — Cursor will analyze the output)")
            if product_url:
                print(f"   Product URL: {product_url}")
            result = processor.analyze_product_by_name(
                product_name,
                product_url=product_url,
                crawl_depth=args.crawl_depth,
                skip_llm=True,
            )
        else:
            # ── Multi-source discovery mode ──────────────────────────
            product_name = product_arg
            product_url = args.url if args.url else (product_arg if is_url else None)
            print(f"📡 Running multi-source discovery for '{product_name}'")
            if product_url:
                print(f"   Product URL: {product_url}")
            result = processor.analyze_product_by_name(
                product_name,
                product_url=product_url,
                crawl_depth=args.crawl_depth,
            )

        # Save output
        output_file = processor.save_output(result, args.output, format=args.format)

        # Print summary
        analysis = result.get("analysis", {})
        print("\n" + "=" * 60)
        print("ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Product: {result.get('product_name', result['extracted_data'].get('title', 'Unknown'))}")

        # Show discovery metadata if available
        discovery = result.get("discovery_metadata")
        if discovery:
            print(f"\nDiscovery Sources: {', '.join(discovery.get('sources_used', []))}")
            print(f"Overall Confidence: {discovery.get('overall_confidence', 'N/A')}")

        print(f"\nSummary: {analysis.get('summary', 'N/A')[:200]}")
        print(f"\nCategory: {analysis.get('category', 'Unknown')}")

        caps = analysis.get("capabilities", [])
        print(f"\nCapabilities ({len(caps)}):")
        for cap in caps[:8]:
            print(f"  • {cap}")
        if len(caps) > 8:
            print(f"  ... and {len(caps) - 8} more")

        endpoints = analysis.get("api_endpoints", [])
        if endpoints:
            print(f"\nAPI Endpoints ({len(endpoints)}):")
            for ep in endpoints[:5]:
                print(f"  • {ep}")
            if len(endpoints) > 5:
                print(f"  ... and {len(endpoints) - 5} more")

        sdks = analysis.get("sdk_languages", [])
        if sdks:
            print(f"\nSDK Languages: {', '.join(sdks)}")

        auth = analysis.get("auth_methods", [])
        if auth:
            print(f"Auth Methods: {', '.join(auth)}")

        print(f"\n✅ Full analysis saved to: {output_file}")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
