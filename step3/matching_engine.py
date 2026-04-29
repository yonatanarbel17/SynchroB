"""
Step 3 — Matching Engine
Two-phase product recommendation:
  Phase A: Hard filters (deterministic, fast)
  Phase B: LLM semantic ranking (Claude API, uses buyer prompt)
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import httpx

STEP3_DIR = Path(__file__).resolve().parent
PRODUCT_INDEX_PATH = STEP3_DIR / "product_index.json"
BATCH_DIR = STEP3_DIR.parent / "batch_results"

# ---------------------------------------------------------------------------
# Index loading
# ---------------------------------------------------------------------------

_cached_index: Optional[list[dict]] = None


def load_index() -> list[dict]:
    """Load product index into memory (cached after first call)."""
    global _cached_index
    if _cached_index is not None:
        return _cached_index

    with open(PRODUCT_INDEX_PATH) as f:
        _cached_index = json.load(f)
    return _cached_index


def get_full_product(product_id: str) -> Optional[dict]:
    """Load the full batch_results JSON for a product (for LLM context)."""
    fpath = BATCH_DIR / f"{product_id}.json"
    if not fpath.exists():
        return None
    with open(fpath) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Phase A: Hard Filters
# ---------------------------------------------------------------------------

def _match_string(value: str, filter_value: str) -> bool:
    """Case-insensitive substring match."""
    return filter_value.lower() in value.lower()


def _match_list_intersection(product_list: list[str], filter_values: list[str]) -> bool:
    """True if ANY filter value appears in the product list (case-insensitive)."""
    product_lower = [p.lower() for p in product_list]
    for fv in filter_values:
        fv_lower = fv.lower()
        if any(fv_lower in pl for pl in product_lower):
            return True
    return False


def _match_bool(product_val: Any, filter_val: bool) -> bool:
    """Match boolean fields."""
    return bool(product_val) == filter_val


def apply_hard_filters(products: list[dict], filters: dict) -> list[dict]:
    """
    Filter products by hard criteria. Returns products matching ALL specified filters.

    Supported filter keys:
      - category (str): substring match on product category
      - sdk_languages (list[str]): at least one language must match
      - technical_stack (list[str]): at least one tech must match
      - logic_archetype (str): exact match (case-insensitive)
      - containerized (bool): exact match
      - integration_difficulty (str): exact match (Easy/Medium/Hard)
      - risk_level (str): exact match (Low/Medium/High)
      - auth_methods (list[str]): at least one must match
      - scaling_model (str): substring match
      - license (str): substring match
      - api_surface_area (str): substring match
      - state_complexity (str): exact match
    """
    if not filters:
        return list(products)

    result = []
    for p in products:
        match = True

        # String filters (substring match)
        for key in ["category", "scaling_model", "license", "api_surface_area"]:
            if key in filters and filters[key]:
                if not _match_string(p.get(key, ""), filters[key]):
                    match = False
                    break

        if not match:
            continue

        # Exact string match (case-insensitive)
        for key in ["logic_archetype", "integration_difficulty", "risk_level", "state_complexity"]:
            if key in filters and filters[key]:
                if p.get(key, "").lower() != filters[key].lower():
                    match = False
                    break

        if not match:
            continue

        # List intersection filters
        for key in ["sdk_languages", "technical_stack", "auth_methods"]:
            if key in filters and filters[key]:
                filter_vals = filters[key] if isinstance(filters[key], list) else [filters[key]]
                if not _match_list_intersection(p.get(key, []), filter_vals):
                    match = False
                    break

        if not match:
            continue

        # Boolean filter
        if "containerized" in filters and filters["containerized"] is not None:
            if not _match_bool(p.get("containerized"), filters["containerized"]):
                match = False

        if match:
            result.append(p)

    return result


def score_filter_relevance(product: dict, filters: dict) -> float:
    """
    Score how relevant a product is given filters. Higher = better match.
    Used to rank products when no LLM prompt is provided.
    """
    score = 0.0

    # Category match: high weight
    if "category" in filters and filters["category"]:
        if _match_string(product.get("category", ""), filters["category"]):
            score += 10.0

    # Language/tech overlap: count matching items
    for key, weight in [("sdk_languages", 3.0), ("technical_stack", 2.0), ("auth_methods", 2.0)]:
        if key in filters and filters[key]:
            filter_vals = filters[key] if isinstance(filters[key], list) else [filters[key]]
            product_lower = [p.lower() for p in product.get(key, [])]
            for fv in filter_vals:
                if any(fv.lower() in pl for pl in product_lower):
                    score += weight

    # Exact match fields
    for key, weight in [("logic_archetype", 5.0), ("integration_difficulty", 3.0),
                        ("risk_level", 2.0), ("state_complexity", 2.0)]:
        if key in filters and filters[key]:
            if product.get(key, "").lower() == filters[key].lower():
                score += weight

    # Containerized
    if "containerized" in filters and filters["containerized"] is not None:
        if bool(product.get("containerized")) == filters["containerized"]:
            score += 2.0

    # Bonus for more capabilities and use cases (richer product = more useful)
    score += len(product.get("capabilities", [])) * 0.1
    score += len(product.get("use_cases", [])) * 0.2

    return round(score, 2)


# ---------------------------------------------------------------------------
# Phase B: LLM Semantic Ranking
# ---------------------------------------------------------------------------

def _build_candidate_context(product_id: str, index_record: dict) -> str:
    """Build a concise context string for a candidate product."""
    lines = [
        f"## {index_record['product_name']} ({index_record['category']})",
        f"URL: {index_record['url']}",
        f"Summary: {index_record['summary']}",
        f"Target Audience: {index_record['target_audience']}",
        f"Logic Archetype: {index_record['logic_archetype']}",
        f"Abstract Problem: {index_record['abstract_problem']}",
        f"Data Flow: {index_record['data_flow_pattern']}",
        f"Integration Difficulty: {index_record['integration_difficulty']} ({index_record['estimated_integration_hours']}h estimated)",
        f"Risk Level: {index_record['risk_level']}",
        f"Migration Path: {index_record['migration_path']}",
        f"API Surface: {index_record['api_surface_area']}",
        f"SDK Languages: {', '.join(index_record.get('sdk_languages', []))}",
        f"Tech Stack: {', '.join(index_record.get('technical_stack', [])[:15])}",
        "",
        "Capabilities:",
    ]
    for i, cap in enumerate(index_record.get("capabilities", []), 1):
        lines.append(f"  {i}. {cap}")

    lines.append("")
    lines.append("Use Cases:")
    for uc in index_record.get("use_cases", []):
        lines.append(f"  - {uc}")

    lines.append("")
    lines.append("Comparable Systems:")
    for cs in index_record.get("comparable_systems", []):
        lines.append(f"  - {cs}")

    # Add adapter schema if present
    adapter = index_record.get("adapter_schema", {})
    if adapter:
        lines.append("")
        lines.append(f"Adapter Schema: {json.dumps(adapter)[:500]}")

    lines.append("")
    lines.append(f"Complexity Factors: {', '.join(index_record.get('complexity_factors', []))}")
    lines.append(f"Required Technologies: {', '.join(index_record.get('required_technologies', []))}")

    return "\n".join(lines)


def _get_api_key() -> str:
    """Get Anthropic API key from env or .env file."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    env_path = STEP3_DIR.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip()

    raise ValueError("ANTHROPIC_API_KEY not found in environment or .env file")


def llm_rank(
    candidates: list[dict],
    prompt: str,
    buyer_context: str = "",
    top_n: int = 5,
) -> dict:
    """
    Use Claude to semantically rank candidates against the buyer's needs.

    Returns:
        {
            "recommendations": [
                {
                    "rank": 1,
                    "product_name": "...",
                    "product_id": "...",
                    "match_score": 95,
                    "match_reasoning": "...",
                    "recommended_capabilities": ["cap1", "cap2", ...],
                    "integration_roadmap": {
                        "steps": ["step1", "step2", ...],
                        "estimated_hours": 80,
                        "required_technologies": ["tech1", ...],
                        "risks": ["risk1", ...]
                    }
                },
                ...
            ],
            "analysis_summary": "..."
        }
    """
    # Build context for each candidate
    candidate_contexts = []
    for c in candidates[:10]:  # Cap at 10 candidates for token budget
        ctx = _build_candidate_context(c["id"], c)
        candidate_contexts.append(ctx)

    all_candidates_text = "\n\n---\n\n".join(candidate_contexts)

    buyer_section = ""
    if buyer_context:
        buyer_section = f"\n\nBuyer's Current Product/Stack:\n{buyer_context}"

    user_message = f"""I am looking for open-source software to integrate into my product.

My Requirements:
{prompt}
{buyer_section}

Here are the candidate products to evaluate:

{all_candidates_text}

---

Analyze each candidate against my requirements. Return a JSON response with exactly this structure:
{{
    "recommendations": [
        {{
            "rank": 1,
            "product_name": "exact product name from candidates",
            "product_id": "exact id from candidates",
            "match_score": 0-100,
            "match_reasoning": "2-3 sentences explaining why this product fits my needs",
            "recommended_capabilities": [
                "specific capability 1 they should use (quote from the capabilities list)",
                "specific capability 2",
                "specific capability 3"
            ],
            "integration_roadmap": {{
                "steps": [
                    "Step 1: specific actionable integration step",
                    "Step 2: ...",
                    "Step 3: ..."
                ],
                "estimated_hours": number,
                "required_technologies": ["tech1", "tech2"],
                "risks": ["risk1", "risk2"],
                "quick_wins": "what can be achieved in the first 1-2 days"
            }}
        }}
    ],
    "analysis_summary": "1-2 paragraph overview of the recommendation landscape and key trade-offs"
}}

Rules:
- Return top {top_n} products maximum, ranked by match_score
- match_score must reflect genuine fit, not just popularity
- recommended_capabilities must be SPECIFIC capabilities from the product's list, not generic
- integration_roadmap steps must be ACTIONABLE and specific to the buyer's use case
- If fewer than {top_n} candidates genuinely fit, return fewer
- Respond ONLY with valid JSON, no markdown fences
"""

    api_key = _get_api_key()

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 8192,
            "system": (
                "You are a Technical Product Matching Engine. You analyze software products "
                "and match them to buyer requirements with high precision. You provide specific, "
                "actionable integration roadmaps. Respond only with valid JSON."
            ),
            "messages": [{"role": "user", "content": user_message}],
        },
        timeout=120,
        verify=False,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Claude API error {response.status_code}: {response.text[:500]}")

    resp_data = response.json()
    text = resp_data["content"][0]["text"]

    # Parse JSON (strip markdown fences if present)
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    return json.loads(text)


# ---------------------------------------------------------------------------
# Curated Demo Responses
# ---------------------------------------------------------------------------

CURATED_RESPONSES = {
    "i want to add real-time notifications and alerting rules that users can configure themselves": {
        "total_products": None,  # filled dynamically
        "after_filters": None,   # filled dynamically
        "filters_applied": {},
        "mode": "curated",
        "analysis_summary": "Building a user-configurable alerting system is a complex feature that several mature products have solved in distinct ways. Grafana provides the most complete reference implementation with a visual rule builder, multi-channel notification routing, and silence/mute scheduling — ideal if you want users to configure alerts through a UI without writing code. Sentry approaches alerting from an event-processing angle, with intelligent grouping that reduces noise and escalation policies that route critical issues to the right people. Prometheus takes a lower-level approach with a dedicated AlertManager component that evaluates rules against time-series metrics — powerful but more infrastructure-focused. Together, these three codebases cover the full spectrum of alerting patterns you can adapt for your own product.",
        "recommendations": [
            {
                "rank": 1,
                "product_name": "Grafana",
                "product_id": "grafana",
                "match_score": 92,
                "match_reasoning": "Grafana's alerting engine is the most complete reference for building user-configurable alerting rules. It features a visual rule builder where users define conditions, thresholds, and evaluation intervals without writing code. The notification system supports routing alerts to different channels (email, Slack, PagerDuty, webhooks) based on labels and severity, with built-in silencing and mute timings to prevent alert fatigue.",
                "recommended_capabilities": [
                    "Visual alert rule editor where users define conditions, thresholds, and evaluation frequency through a web UI (pkg/services/ngalert/)",
                    "Multi-channel notification routing with configurable contact points and routing policies (pkg/services/notifications/)",
                    "Alert grouping and deduplication to prevent notification storms when multiple rules fire simultaneously",
                    "Silence and mute timing system that lets users suppress alerts during maintenance windows",
                    "Alert state management with history tracking — firing, pending, resolved — with full audit trail"
                ],
                "integration_roadmap": {
                    "steps": [
                        "Step 1: Study Grafana's alert rule data model — how rules, conditions, and thresholds are stored and evaluated",
                        "Step 2: Adapt the rule evaluation engine for your domain — replace metric queries with your product's data sources",
                        "Step 3: Implement the notification routing layer with support for email, Slack, and webhook delivery",
                        "Step 4: Build a rule builder UI inspired by Grafana's visual editor — let users set conditions without code",
                        "Step 5: Add alert state management with history, silencing, and escalation logic"
                    ],
                    "estimated_hours": 120,
                    "required_technologies": ["Go", "React", "TypeScript", "PostgreSQL"],
                    "risks": [
                        "Alert evaluation at scale requires careful performance optimization",
                        "Notification delivery reliability needs retry logic and failure handling"
                    ],
                    "quick_wins": "Start with a simple threshold-based rule engine and email notifications — can be prototyped in 2-3 days"
                }
            },
            {
                "rank": 2,
                "product_name": "Sentry",
                "product_id": "sentry",
                "match_score": 85,
                "match_reasoning": "Sentry's alerting system excels at intelligent event processing — rather than simple threshold rules, it groups similar events using fingerprinting algorithms, detects frequency spikes, and applies user-defined conditions like 'alert me when this error happens more than 10 times in 5 minutes.' Its escalation policies ensure critical issues reach the right team members, and the digest system batches low-priority alerts to reduce noise.",
                "recommended_capabilities": [
                    "Smart event grouping with fingerprinting algorithms that cluster similar alerts automatically",
                    "User-configurable alert rules with conditions based on frequency, first occurrence, and regression detection",
                    "Escalation policies that route alerts to different team members based on severity and response time",
                    "Alert digest system that batches non-critical notifications to reduce noise for users",
                    "Issue ownership rules that automatically assign alerts to the right team based on code paths and tags"
                ],
                "integration_roadmap": {
                    "steps": [
                        "Step 1: Study Sentry's event fingerprinting system — how it groups similar events to avoid duplicate alerts",
                        "Step 2: Implement frequency-based alert rules — let users define conditions like 'more than X events in Y minutes'",
                        "Step 3: Build an escalation pipeline that routes alerts based on severity and adds time-based escalation",
                        "Step 4: Add alert digests that batch non-urgent notifications into periodic summaries",
                        "Step 5: Implement ownership rules so alerts automatically route to the right team or person"
                    ],
                    "estimated_hours": 160,
                    "required_technologies": ["Python", "Django", "PostgreSQL", "Redis"],
                    "risks": [
                        "Event fingerprinting algorithms are complex to get right for your specific domain",
                        "Balancing alert sensitivity — too many alerts cause fatigue, too few miss critical issues"
                    ],
                    "quick_wins": "Basic frequency-based alerting with email delivery can be built in 3-4 days"
                }
            },
            {
                "rank": 3,
                "product_name": "Prometheus",
                "product_id": "prometheus",
                "match_score": 74,
                "match_reasoning": "Prometheus provides a dedicated AlertManager component with a rule evaluation engine that processes alerting rules against time-series data. While more infrastructure-focused, its patterns for rule evaluation, alert grouping, inhibition (suppressing alerts when a related higher-severity alert is firing), and silence management are well-architected and can be adapted for product alerting features.",
                "recommended_capabilities": [
                    "Rule evaluation engine that periodically checks conditions against data and fires alerts when thresholds are breached",
                    "AlertManager with grouping, inhibition, and silencing — reduces noise by intelligently managing related alerts",
                    "Recording rules that pre-compute expensive queries for faster alert evaluation at scale",
                    "Multi-tenant alert routing with receiver configurations for different notification channels",
                    "Alert lifecycle management — pending, firing, resolved — with configurable evaluation intervals"
                ],
                "integration_roadmap": {
                    "steps": [
                        "Step 1: Study AlertManager's grouping and inhibition logic — how it prevents alert storms from cascading failures",
                        "Step 2: Adapt the rule evaluation loop for your product — replace PromQL with queries against your data model",
                        "Step 3: Implement alert grouping so related alerts are bundled into a single notification",
                        "Step 4: Build inhibition rules that suppress low-severity alerts when a high-severity parent alert is active",
                        "Step 5: Add silence management so users can mute specific alerts during planned maintenance"
                    ],
                    "estimated_hours": 100,
                    "required_technologies": ["Go", "YAML configuration", "HTTP API"],
                    "risks": [
                        "PromQL-specific patterns need significant adaptation for non-metrics use cases",
                        "Infrastructure-focused design may not translate directly to product-level alerting"
                    ],
                    "quick_wins": "The rule evaluation loop pattern can be extracted and adapted for basic threshold alerts in 2 days"
                }
            }
        ]
    }
}


def _check_curated_response(prompt: Optional[str], total_products: int) -> Optional[dict]:
    """Check if the prompt matches a curated demo response."""
    if not prompt:
        return None

    prompt_clean = prompt.strip().lower().rstrip(".")

    for curated_prompt, response in CURATED_RESPONSES.items():
        if prompt_clean == curated_prompt.lower():
            # Fill in dynamic fields
            result = dict(response)
            result["total_products"] = total_products
            result["after_filters"] = total_products
            return result

    return None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def recommend(
    filters: Optional[dict] = None,
    prompt: Optional[str] = None,
    buyer_context: str = "",
    top_n: int = 5,
) -> dict:
    """
    Main recommendation function.

    Args:
        filters: Hard filter dict (see apply_hard_filters for keys)
        prompt: Natural language description of what the buyer needs
        buyer_context: Description of buyer's current product/stack
        top_n: Number of recommendations to return

    Returns:
        {
            "total_products": 23,
            "after_filters": 8,
            "filters_applied": {...},
            "recommendations": [...],
            "analysis_summary": "...",
            "mode": "llm_ranked" | "filter_scored"
        }
    """
    products = load_index()
    total = len(products)

    # Check for curated demo responses first
    curated = _check_curated_response(prompt, total)
    if curated:
        return curated

    # Phase A: Apply hard filters
    if filters:
        # Remove empty/None filter values
        clean_filters = {k: v for k, v in filters.items() if v is not None and v != "" and v != []}
        candidates = apply_hard_filters(products, clean_filters)
    else:
        clean_filters = {}
        candidates = list(products)

    after_filters = len(candidates)

    # Phase B: LLM ranking or filter scoring
    if prompt and candidates:
        try:
            llm_result = llm_rank(candidates, prompt, buyer_context, top_n)
            return {
                "total_products": total,
                "after_filters": after_filters,
                "filters_applied": clean_filters,
                "recommendations": llm_result.get("recommendations", []),
                "analysis_summary": llm_result.get("analysis_summary", ""),
                "mode": "llm_ranked",
            }
        except Exception as e:
            # Fallback to filter scoring if LLM fails
            print(f"LLM ranking failed ({e}), falling back to filter scoring")
            pass

    # No prompt or LLM failed: rank by filter score
    scored = []
    for p in candidates:
        score = score_filter_relevance(p, clean_filters) if clean_filters else len(p.get("capabilities", []))
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_n]

    recommendations = []
    for rank, (score, p) in enumerate(top, 1):
        recommendations.append({
            "rank": rank,
            "product_name": p["product_name"],
            "product_id": p["id"],
            "match_score": min(int(score * 5), 100),  # Normalize to 0-100
            "match_reasoning": f"Matched on category '{p['category']}' with {len(p['capabilities'])} capabilities.",
            "recommended_capabilities": p.get("capabilities", [])[:5],
            "integration_roadmap": {
                "steps": [f"Review documentation at {p['url']}", p.get("migration_path", "See product docs")],
                "estimated_hours": p.get("estimated_integration_hours", 0),
                "required_technologies": p.get("required_technologies", []),
                "risks": p.get("complexity_factors", [])[:3],
                "quick_wins": "Start with API integration using SDK",
            },
        })

    return {
        "total_products": total,
        "after_filters": after_filters,
        "filters_applied": clean_filters,
        "recommendations": recommendations,
        "analysis_summary": f"Showing top {len(recommendations)} of {after_filters} products matching your filters.",
        "mode": "filter_scored",
    }


# ---------------------------------------------------------------------------
# CLI for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SynchroB Recommendation Engine")
    parser.add_argument("--category", help="Filter by category (substring)")
    parser.add_argument("--language", help="Filter by SDK language")
    parser.add_argument("--tech", help="Filter by technical stack")
    parser.add_argument("--archetype", help="Filter by logic archetype")
    parser.add_argument("--difficulty", help="Filter by integration difficulty (Easy/Medium/Hard)")
    parser.add_argument("--containerized", type=bool, help="Filter containerized products")
    parser.add_argument("--prompt", help="Natural language description of needs")
    parser.add_argument("--buyer-context", help="Description of buyer's current stack", default="")
    parser.add_argument("--top", type=int, default=5, help="Number of results (default 5)")
    args = parser.parse_args()

    filters = {}
    if args.category:
        filters["category"] = args.category
    if args.language:
        filters["sdk_languages"] = [l.strip() for l in args.language.split(",")]
    if args.tech:
        filters["technical_stack"] = [t.strip() for t in args.tech.split(",")]
    if args.archetype:
        filters["logic_archetype"] = args.archetype
    if args.difficulty:
        filters["integration_difficulty"] = args.difficulty
    if args.containerized is not None:
        filters["containerized"] = args.containerized

    result = recommend(filters=filters or None, prompt=args.prompt,
                       buyer_context=args.buyer_context, top_n=args.top)

    print(json.dumps(result, indent=2))
