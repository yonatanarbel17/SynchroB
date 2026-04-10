# SynchroB Frontend — Complete Build Prompt for Lovable

## What is SynchroB?

SynchroB is a product recommendation engine for open-source software. A user (buyer) comes in, applies filters and/or writes a natural language prompt describing what they need, and the engine returns the top 5 open-source products that match — with specific capabilities to use and a step-by-step integration roadmap.

The backend API is already live at: **https://synchrob-api.onrender.com**

Interactive API docs: **https://synchrob-api.onrender.com/docs**

---

## API Endpoints

### 1. `GET /health`
Health check. Returns `{"status": "healthy", "products_indexed": 23}`.

### 2. `GET /filters`
Returns all available filter options for populating dropdowns/checkboxes. The frontend should call this on page load to dynamically build the filter UI.

**Response structure:**
```json
{
  "categories": [
    "Agricultural Data Management Platform",
    "Business Intelligence Platform",
    "Columnar Database Management System",
    "Decentralized Social Media Platform",
    "Development Environment Management Tool",
    "Distributed SQL Database",
    "E-commerce Platform",
    "Enterprise Resource Planning (ERP) System",
    "Error Monitoring and Application Performance Management Platform",
    "Game Engine",
    "Git Repository Management Platform",
    "Home Automation Platform",
    "Identity and Access Management (IAM) Server",
    "Integrated Development Environment",
    "Low-Code Application Platform",
    "Monitoring and Observability Platform",
    "Software Reverse Engineering Framework",
    "Team Chat Platform",
    "Team Communication Platform",
    "Text Editor / IDE"
  ],
  "logic_archetypes": [
    "Authentication/Authorization Service",
    "Data Aggregator",
    "Event-Driven Reactor",
    "Plugin Host",
    "Simulation Engine",
    "Stateful Orchestrator"
  ],
  "state_complexities": ["Distributed", "Entity-scoped", "Global mutable", "Session-scoped"],
  "technical_stack": ["...232 values — show as searchable multi-select..."],
  "sdk_languages": ["...34 values — show as multi-select chips..."],
  "auth_methods": ["...110 values — show as searchable multi-select..."],
  "integration_difficulties": ["High", "Medium"],
  "risk_levels": ["High", "Medium"],
  "scaling_models": ["...23 values..."],
  "api_surface_areas": ["Large (50+)", "Library API", "Medium (10-50)"],
  "containerized": [true, false]
}
```

### 3. `GET /products`
Returns a summary list of all 23 indexed products. Use this for a "Browse All Products" page or catalog view.

**Response (array of objects):**
```json
[
  {
    "id": "grafana",
    "product_name": "grafana",
    "url": "https://github.com/grafana/grafana.git",
    "category": "Monitoring and Observability Platform",
    "summary": "Grafana is a comprehensive monitoring and observability platform...",
    "logic_archetype": "Plugin Host",
    "integration_difficulty": "Medium",
    "sdk_languages": ["Go", "JavaScript/TypeScript", "Python", "Ruby"],
    "capabilities_count": 25,
    "use_cases_count": 5
  }
]
```

### 4. `GET /products/{product_id}`
Returns full detail for a single product. Use this for a product detail page. The `product_id` is the `id` field from the products list (e.g., "grafana", "neovim", "magento2").

**Response:**
```json
{
  "index": {
    "id": "grafana",
    "product_name": "grafana",
    "url": "...",
    "category": "Monitoring and Observability Platform",
    "summary": "...",
    "target_audience": "...",
    "technical_stack": ["Go", "React", "TypeScript", "..."],
    "sdk_languages": ["Go", "JavaScript/TypeScript", "..."],
    "capabilities": ["capability 1 with file evidence", "capability 2", "..."],
    "use_cases": ["use case 1", "use case 2", "..."],
    "logic_archetype": "Plugin Host",
    "abstract_problem": "...",
    "data_flow_pattern": "...",
    "state_complexity": "Entity-scoped",
    "containerized": true,
    "integration_difficulty": "Medium",
    "estimated_integration_hours": 120,
    "required_technologies": ["Go 1.25.8", "TypeScript/React 18", "..."],
    "complexity_factors": ["Plugin signature verification system", "..."],
    "risk_level": "Medium",
    "migration_path": "Extract plugin host framework and...",
    "api_surface_area": "Medium (10-50)",
    "comparable_systems": ["similar system 1", "similar system 2", "..."],
    "project_health": {
      "stars": 0,
      "contributors": 0,
      "last_commit": "",
      "activity_level": "Unknown"
    }
  },
  "full_analysis": { "...complete raw analysis from pipeline..." }
}
```

### 5. `POST /recommend` ⭐ (Main endpoint)
The core recommendation engine. Accepts filters and/or a natural language prompt. Returns top N ranked products with match reasoning, recommended capabilities, and integration roadmaps.

**Request body:**
```json
{
  "filters": {
    "category": "E-commerce",
    "sdk_languages": ["Python", "PHP"],
    "logic_archetype": "Plugin Host",
    "technical_stack": ["React"],
    "containerized": true,
    "integration_difficulty": "Medium",
    "risk_level": "Medium",
    "state_complexity": "Entity-scoped",
    "api_surface_area": "Large (50+)"
  },
  "prompt": "I need an e-commerce backend with strong plugin support and Python SDK for my Django SaaS",
  "buyer_context": "We run a Django-based SaaS with PostgreSQL and Redis",
  "top_n": 5
}
```

**All fields are optional except: at least one of `filters` or `prompt` must be provided.**

**Filter keys reference:**
| Key | Type | Matching |
|-----|------|----------|
| `category` | string | Substring match (case-insensitive) |
| `sdk_languages` | string[] | At least one must match |
| `technical_stack` | string[] | At least one must match |
| `logic_archetype` | string | Exact match (case-insensitive) |
| `containerized` | boolean | Exact match |
| `integration_difficulty` | string | Exact match ("Medium" or "High") |
| `risk_level` | string | Exact match ("Medium" or "High") |
| `auth_methods` | string[] | At least one must match |
| `state_complexity` | string | Exact match |
| `api_surface_area` | string | Substring match |
| `scaling_model` | string | Substring match |
| `license` | string | Substring match |

**Response:**
```json
{
  "total_products": 23,
  "after_filters": 2,
  "filters_applied": {
    "category": "E-commerce",
    "sdk_languages": ["Python", "PHP"]
  },
  "mode": "llm_ranked",
  "analysis_summary": "A 1-2 paragraph overview of the recommendation landscape and key trade-offs between the top results...",
  "recommendations": [
    {
      "rank": 1,
      "product_name": "magento2",
      "product_id": "magento2",
      "match_score": 95,
      "match_reasoning": "2-3 sentences explaining why this product fits the buyer's needs specifically",
      "recommended_capabilities": [
        "Processes product catalog management with configurable attributes and inventory tracking (app/code/Magento/Catalog/)",
        "Handles customer authentication and account management with session persistence (app/code/Magento/Customer/)",
        "Integrates payment gateways through extensible payment method framework (app/code/Magento/Payment/)"
      ],
      "integration_roadmap": {
        "steps": [
          "Step 1: Set up Magento development environment with Docker",
          "Step 2: Install Python SDK and configure REST API access",
          "Step 3: Build custom module for Django integration",
          "Step 4: Implement product sync pipeline",
          "Step 5: Deploy and test end-to-end"
        ],
        "estimated_hours": 2000,
        "required_technologies": ["PHP 8.3+", "MySQL/MariaDB", "Redis", "Composer"],
        "risks": ["200+ module interdependencies", "Complex EAV model"],
        "quick_wins": "Basic REST API integration with product catalog in 1-2 days"
      }
    }
  ]
}
```

**Two response modes:**
- `"mode": "llm_ranked"` — Claude AI analyzed the candidates and ranked them (when prompt is provided). Richer reasoning and roadmaps.
- `"mode": "filter_scored"` — Deterministic scoring based on filter matches only (when no prompt). Faster, no API cost, but less detailed reasoning.

---

## Suggested Pages & UI Structure

### Page 1: Landing / Search Page
The main page. Contains:
- **Hero section** with headline like "Find the perfect open-source tool for your project"
- **Filter panel** (sidebar or collapsible section):
  - Category dropdown (single select) — populated from `GET /filters` → `categories`
  - SDK Languages multi-select chips — from `sdk_languages`
  - Logic Archetype dropdown — from `logic_archetypes`
  - Integration Difficulty toggle/dropdown — from `integration_difficulties`
  - Containerized toggle (yes/no/any)
  - Technical Stack searchable multi-select — from `technical_stack` (232 options, needs search)
  - Advanced filters (collapsible): risk_level, state_complexity, api_surface_area
- **Prompt textarea** — "Describe what you're looking for..." with placeholder text
- **Buyer Context textarea** (optional, collapsible) — "Describe your current stack..."
- **"Find Products" button** → calls `POST /recommend`

### Page 2: Results Page
Displays after recommendation call returns:
- **Summary banner** showing: `total_products` → `after_filters` → `recommendations.length` (funnel visualization)
- **Analysis summary** paragraph (from `analysis_summary`)
- **Result cards** for each recommendation:
  - Rank badge (#1, #2, etc.)
  - Product name + category
  - Match score (show as percentage bar or badge, color-coded: green >80, yellow 50-80, red <50)
  - Match reasoning paragraph
  - **Recommended Capabilities** section — bulleted list of the 3-5 specific capabilities
  - **Integration Roadmap** section (collapsible):
    - Numbered steps
    - Estimated hours badge
    - Required technologies as chips/tags
    - Risks as warning items
    - Quick wins highlight
  - "View Full Details" link → navigates to product detail page

### Page 3: Product Detail Page
Route: `/products/{id}`
Calls `GET /products/{product_id}` and displays the full product profile:
- Product name, category, URL (link to GitHub)
- Summary paragraph
- Target audience
- All capabilities (full list of 25)
- Use cases
- Technical stack (as tags)
- SDK languages (as tags)
- Architecture details (logic archetype, data flow pattern, state complexity)
- Integration info (difficulty, estimated hours, required technologies, risks)
- Comparable systems
- Migration path

### Page 4: Browse Catalog
Calls `GET /products` and shows all 23 products as a card grid:
- Product name, category, archetype, difficulty badge
- Click to navigate to detail page
- Optional: client-side filtering/sorting

---

## UI/UX Guidelines

- **Color scheme**: Professional, tech-oriented. Dark mode preferred. Suggested palette: deep navy background, white/light text, accent color for scores and CTAs.
- **Typography**: Clean sans-serif (Inter, Geist, or similar)
- **Loading states**: The `POST /recommend` with a prompt takes 10-30 seconds (LLM call). Show a loading animation with text like "AI is analyzing products for you..." Don't let the user think it's broken.
- **Empty states**: If no products match the filters, show a helpful message suggesting to broaden filters.
- **Error handling**: If the API returns 502 (LLM error), show "AI ranking temporarily unavailable, showing filter-based results" and retry without the prompt.
- **Responsive**: Must work on desktop and tablet. Mobile is a nice-to-have.
- **The filter panel should NOT overwhelm the user**: Start with 3-4 primary filters visible (category, languages, difficulty, prompt). Put the rest behind an "Advanced Filters" toggle.

---

## Technical Notes

- **CORS is enabled** on the backend — any origin can call the API.
- **No authentication required** — all endpoints are public.
- **Rate limiting**: The `/recommend` endpoint with a prompt uses Claude AI under the hood. Don't spam it — debounce the submit button, disable it while loading.
- **The API is on Render free tier** — first request after idle may take 30-60 seconds to cold start. Show a loading state.
- **All product IDs are lowercase repo names**: "grafana", "neovim", "magento2", "Rocket.Chat", "ClickHouse" (some have uppercase/dots — use exactly as returned by the API).

---

## Quick Start — Minimum Viable Frontend

If you want to get something working fast, start with just:
1. Call `GET /filters` on mount → populate a category dropdown
2. Add a text input for the prompt
3. Call `POST /recommend` with `{"filters": {"category": selectedCategory}, "prompt": userInput}`
4. Display the `recommendations` array as cards

That's a working product in ~100 lines of React. Then iterate from there.
