"""
Step 3 — FastAPI Server
REST API for the SynchroB Recommendation Engine.

Endpoints:
  GET  /filters            — available filter options for frontend dropdowns
  GET  /products           — list all indexed products (summary view)
  GET  /products/{id}      — full detail for one product
  POST /recommend          — get top N product recommendations
  GET  /health             — health check
"""

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from matching_engine import load_index, get_full_product, recommend

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SynchroB Recommendation Engine",
    description="Find the best open-source products for your needs",
    version="1.0.0",
)

# CORS — allow Lovable and any frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STEP3_DIR = Path(__file__).resolve().parent
FILTER_OPTIONS_PATH = STEP3_DIR / "filter_options.json"


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class RecommendRequest(BaseModel):
    filters: Optional[dict[str, Any]] = Field(
        default=None,
        description="Hard filters to narrow candidates. Keys: category, sdk_languages, "
                    "technical_stack, logic_archetype, containerized, integration_difficulty, "
                    "risk_level, auth_methods, scaling_model, license, api_surface_area, state_complexity",
        json_schema_extra={
            "example": {
                "category": "E-commerce",
                "sdk_languages": ["Python", "PHP"],
                "logic_archetype": "Plugin Host",
            }
        },
    )
    prompt: Optional[str] = Field(
        default=None,
        description="Natural language description of what you're looking for",
        json_schema_extra={"example": "I need an e-commerce backend with strong plugin support and Python SDK"},
    )
    buyer_context: Optional[str] = Field(
        default="",
        description="Description of your current product/stack for better matching",
        json_schema_extra={"example": "We run a Django-based SaaS with PostgreSQL and Redis"},
    )
    top_n: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of recommendations to return (1-10)",
    )


class ProductSummary(BaseModel):
    id: str
    product_name: str
    url: str
    category: str
    summary: str
    logic_archetype: str
    integration_difficulty: str
    sdk_languages: list[str]
    capabilities_count: int
    use_cases_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    products = load_index()
    return {"status": "healthy", "products_indexed": len(products)}


@app.get("/filters")
async def get_filters():
    """Return all available filter options for frontend dropdowns."""
    if not FILTER_OPTIONS_PATH.exists():
        raise HTTPException(status_code=500, detail="Filter options not built. Run build_index.py first.")

    with open(FILTER_OPTIONS_PATH) as f:
        return json.load(f)


@app.get("/products", response_model=list[ProductSummary])
async def list_products():
    """List all indexed products (summary view)."""
    products = load_index()
    return [
        ProductSummary(
            id=p["id"],
            product_name=p["product_name"],
            url=p["url"],
            category=p["category"],
            summary=p["summary"][:200] + "..." if len(p.get("summary", "")) > 200 else p.get("summary", ""),
            logic_archetype=p.get("logic_archetype", "Unknown"),
            integration_difficulty=p.get("integration_difficulty", "Unknown"),
            sdk_languages=p.get("sdk_languages", []),
            capabilities_count=len(p.get("capabilities", [])),
            use_cases_count=len(p.get("use_cases", [])),
        )
        for p in products
    ]


@app.get("/products/{product_id}")
async def get_product(product_id: str):
    """Get full detail for a specific product."""
    # First check index
    products = load_index()
    index_record = next((p for p in products if p["id"] == product_id), None)

    if not index_record:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    # Load full batch result for complete data
    full = get_full_product(product_id)

    return {
        "index": index_record,
        "full_analysis": full,
    }


@app.post("/recommend")
async def recommend_products(request: RecommendRequest):
    """
    Get product recommendations based on filters and/or natural language prompt.

    - Filters alone: returns products ranked by filter match score (no API cost)
    - Prompt alone: all products sent to Claude for semantic ranking
    - Filters + prompt: filtered products sent to Claude for ranking (optimal)
    """
    if not request.filters and not request.prompt:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of 'filters' or 'prompt'",
        )

    try:
        result = recommend(
            filters=request.filters,
            prompt=request.prompt,
            buyer_context=request.buyer_context or "",
            top_n=request.top_n,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"LLM API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
