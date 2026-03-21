"""
Centralized constants and configuration for the SynchroB pipeline.

This module consolidates all hardcoded dictionaries, keyword lists, and templates
from across the codebase (processor.py, generalizer.py, etc.) into a single
source of truth for easy maintenance and updates.
"""

from typing import Dict, List, Set


# ============================================================================
# TECHNOLOGY KEYWORDS
# ============================================================================
# Mapping of technology categories to lists of specific keywords.
# Used consistently across discovery (web_scraping.py), processing (processor.py),
# and generalization (generalizer.py) for tech stack extraction.

TECH_KEYWORDS: Dict[str, List[str]] = {
    "programming_languages": [
        "python", "javascript", "typescript", "java", "go", "rust",
        "ruby", "php", "c++", "c#", "swift", "kotlin",
    ],
    "frameworks": [
        "react", "vue", "angular", "django", "flask", "express",
        "spring", "laravel", "rails",
    ],
    "databases": [
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "cassandra", "dynamodb",
    ],
    "cloud": [
        "aws", "azure", "gcp", "google cloud", "amazon web services",
    ],
    "tools": [
        "docker", "kubernetes", "terraform", "ansible", "jenkins", "git",
    ],
    "apis": ["rest", "graphql", "grpc", "soap"],
    "protocols": ["http", "https", "websocket", "mqtt"],
}


# ============================================================================
# MARKETING WORDS
# ============================================================================
# Set of common marketing superlatives and buzzwords that should be stripped
# during extraction to focus on technical substance.
# Used in Step 1 and Step 2 to clean analysis outputs.

MARKETING_WORDS: Set[str] = {
    "powerful",
    "revolutionary",
    "easy",
    "best-in-class",
    "cutting-edge",
    "world-class",
    "seamless",
    "robust",
    "scalable",
    "enterprise-grade",
    "next-generation",
    "innovative",
    "state-of-the-art",
    "industry-leading",
    "game-changing",
    "disruptive",
    "transformative",
    "leading",
    "trusted",
    "secure",
    "simple",
    "intuitive",
    "flexible",
    "reliable",
}


# ============================================================================
# LOGIC ARCHETYPES
# ============================================================================
# Strict set of architectural patterns/archetypes that products can be
# classified into during Step 2 generalization.
# Used by _infer_logic_archetype() to categorize the core logic pattern.

LOGIC_ARCHETYPES: Dict[str, str] = {
    "Stream Processor": "Processes continuous streams of data/events (Kafka, real-time pipelines)",
    "Batch Optimizer": "Processes data in scheduled batches (ETL, scheduled jobs)",
    "Stateful Orchestrator": "Manages state and workflow orchestration (state machines, workflow engines)",
    "Stateless Transformer": "Transforms data without maintaining state (REST APIs, pure functions)",
    "Matching Engine": "Matches two sides (orders, jobs, users) efficiently (exchanges, job boards)",
    "Search/Index Engine": "Indexes and retrieves data efficiently (search engines, document stores)",
    "Recommendation Engine": "Recommends items based on patterns (collaborative filtering, ML)",
    "Authentication/Authorization Service": "Manages identity and access control",
    "Data Aggregator": "Collects and combines data from multiple sources",
    "API Gateway": "Routes and transforms API requests",
    "CRUD Wrapper": "Basic Create-Read-Update-Delete wrapper around persistence",
    "Event Router": "Routes events to appropriate handlers based on content",
}


# ============================================================================
# ALGORITHM PATTERNS
# ============================================================================
# Mapping of core algorithmic classes to their descriptions.
# Used by _infer_algorithmic_class() to categorize the computational approach.

ALGORITHM_PATTERNS: Dict[str, str] = {
    "Graph Algorithms": "Algorithms that operate on graph structures (traversal, pathfinding, connectivity)",
    "Combinatorial Optimization": "Finds optimal solutions in large combinatorial search spaces",
    "Time-Series Processing": "Analyzes temporal sequences and patterns over time",
    "Linear Algebra": "Matrix operations and linear transformations",
    "Distributed Consensus": "Achieves agreement across distributed systems (Byzantine Fault Tolerance)",
    "Search Algorithms": "Efficient search and retrieval (binary search, indexing)",
    "Statistical Models": "Probabilistic and statistical inference",
    "Neural Networks": "Deep learning and machine learning models",
    "CRUD Operations": "Basic Create-Read-Update-Delete data persistence",
}


# ============================================================================
# DATA CONTRACT TYPES
# ============================================================================
# Levels of strictness for data contracts and schemas.
# Used by _infer_data_contract_strictness() to assess data format requirements.

DATA_CONTRACT_TYPES: List[str] = [
    "Highly Structured",      # Strict schema (OpenAPI, protobuf)
    "Moderately Structured",  # Some schema (JSON with loose shape)
    "Schema-less",            # Unstructured data
    "Unknown",
]


# ============================================================================
# CONCURRENCY MODELS
# ============================================================================
# Types of concurrency and consistency requirements a system may have.
# Used by _infer_concurrency_model() to assess threading/async approach.

CONCURRENCY_MODELS: List[str] = [
    "Asynchronous / Event Loop",           # Async/await, event-driven
    "Multi-threaded / Parallel Processing", # Thread-based concurrency
    "Multi-process / Worker Pool",         # Process-based concurrency
    "Actor Model / Message Passing",       # Actor model (Akka, Erlang)
    "Goroutines / CSP",                    # Go-style CSP (Communicating Sequential Processes)
    "Single-threaded / Sequential",        # No concurrency
]


# ============================================================================
# CONSISTENCY REQUIREMENTS
# ============================================================================
# Types of data consistency guarantees required by systems.
# Used in generalization to assess transactional/eventual consistency needs.

CONSISTENCY_REQUIREMENTS: List[str] = [
    "ACID Compliance Required",     # Strong transactional guarantees
    "Eventually Consistent",        # Eventual consistency acceptable
    "No Consistency Requirements",  # Stateless or cache-friendly
    "Unknown",
]


# ============================================================================
# INDUSTRY MAPPINGS
# ============================================================================
# Cross-industry mappings for identifying when a product can be applied
# to different domains. Used by _map_to_new_industries() in Step 2.

INDUSTRY_MAPPINGS: Dict[str, List[str]] = {
    "order_matching": [
        "E-commerce & Retail",
        "Transportation & Logistics",
        "Human Resources & Recruitment",
        "Social & Networking Platforms",
        "Supply Chain & Manufacturing",
    ],
    "transaction_processing": [
        "E-commerce & Retail",
        "SaaS & Cloud Services",
        "Healthcare & Life Sciences",
        "Education & E-Learning",
        "Government & Public Sector",
    ],
    "search_indexing": [
        "E-commerce & Retail",
        "Legal & Compliance",
        "Healthcare & Life Sciences",
        "Education & E-Learning",
        "Media & Entertainment",
    ],
    "recommendation": [
        "E-commerce & Retail",
        "Media & Entertainment",
        "Education & E-Learning",
        "Healthcare & Life Sciences",
        "Financial Services",
    ],
    "stream_processing": [
        "IoT & Connected Devices",
        "Financial Services",
        "Gaming & Entertainment",
        "Transportation & Logistics",
        "Security & Compliance",
    ],
    "authentication": [
        "Enterprise Software",
        "Healthcare & Life Sciences",
        "Financial Services",
        "Government & Public Sector",
        "Education & E-Learning",
    ],
    "generic": [
        "Enterprise Software",
        "SaaS & Cloud Services",
        "B2B Integrations",
        "Internal Tools & Automation",
        "Developer Tools & Platforms",
    ],
}


# ============================================================================
# SOURCE WEIGHTS
# ============================================================================
# Weighting of discovery sources by authoritativeness for deduplication.
# Used by merger.py to determine which source to prefer when deduplicating facts.
# Higher weight = more authoritative and preferred.

SOURCE_WEIGHTS: Dict[str, int] = {
    "openapi_spec": 95,
    "github_repo": 80,
    "package_registry": 75,
    "web_scrape": 40,
    "llm_knowledge": 30,
}


# ============================================================================
# INTEGRATION KEYWORDS
# ============================================================================
# Keywords used to identify integration mentions in content.
# Used by _extract_integrations() in processor.py.

INTEGRATION_KEYWORDS: List[str] = [
    "integrate", "integration", "connect", "plugin", "add-on",
    "extension", "api", "sdk", "webhook", "oauth"
]


# ============================================================================
# COMMON INTEGRATION SERVICES
# ============================================================================
# Well-known third-party services that may be mentioned in integrations.
# Used by _extract_integrations() to identify specific service mentions.

COMMON_SERVICES: List[str] = [
    "stripe", "paypal", "slack", "github", "jira",
    "salesforce", "zapier", "webhook", "oauth"
]


# ============================================================================
# CAPABILITY EXTRACTION PATTERNS
# ============================================================================
# Regex patterns and keywords used to extract capabilities from content.
# Used by _extract_capabilities() in processor.py.

CAPABILITY_KEYWORDS: List[str] = [
    "feature", "support", "include", "provide", "enable", "allow"
]


# ============================================================================
# USE CASE EXTRACTION KEYWORDS
# ============================================================================
# Keywords that indicate use case statements in content.
# Used by _generate_use_cases() in processor.py.

USE_CASE_KEYWORDS: List[str] = [
    "for", "use case", "ideal for", "perfect for", "designed for"
]


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================
# LLM prompt templates used across the pipeline for consistent analysis.
# These define the exact instructions given to language models.

PROMPT_TEMPLATES: Dict[str, str] = {
    "STEP1_TECHNICAL_EXTRACTOR": """You are a Technical Documentation Extractor. Your goal is to extract ONLY technical facts, stripping all marketing language.

STRIP ALL MARKETING LANGUAGE:
- Remove: "powerful", "easy", "revolutionary", "best-in-class", "millions of users", "cutting-edge"
- Keep: Technical specifications, API endpoints, architecture patterns, functional verbs (processes, transforms, validates)

EVIDENCE REQUIREMENTS:
- Every technical claim must cite its source (file, URL, or section)
- Mark confidence: High (explicitly stated), Medium (inferred from structure), Low (speculative)

PRIORITY:
1. OpenAPI/Swagger specs (weight: 90%)
2. API documentation (weight: 70%)
3. Technical docs (weight: 50%)
4. Landing page (weight: 10%)

URL: {url}
Product: {title}

Content:
{content_preview}

Provide a JSON response with the following structure:
{{
    "summary": "A 2-3 sentence technical summary (NO marketing language). Focus on functional verbs and technical nouns.",
    "capabilities": ["List of technical capabilities with evidence citations"],
    "use_cases": ["List of primary use cases"],
    "technical_stack": ["Technologies EXPLICITLY mentioned with evidence. DO NOT infer technologies not mentioned."],
    "integrations": ["List of integrations EXPLICITLY mentioned"],
    "api_endpoints": ["List of API endpoints with evidence (e.g., 'POST /api/v1/users (found in /docs/api-reference.md)')"],
    "pricing": {{
        "model": "pricing model (e.g., 'freemium', 'subscription', 'one-time', 'usage-based', 'enterprise', 'free', 'unknown')",
        "tiers": ["List of pricing tiers if mentioned"],
        "free_tier": "true/false/unknown",
        "notes": "Any pricing notes or details"
    }},
    "target_audience": "Who is this product for?",
    "category": "Product category",
    "deployment": "Deployment options (e.g., 'cloud', 'on-premise', 'hybrid', 'SaaS', 'self-hosted', 'unknown')",
    "underlying_algorithm": {{
        "problem_type": "What abstract mathematical or structural problem is being solved? (e.g., 'Byzantine Fault Tolerance', 'CRUD wrapper', 'Graph traversal', 'Stream processing')",
        "complexity": "Time/space complexity if inferable (e.g., 'O(n log n)', 'O(1)')",
        "pattern": "Design pattern or algorithmic approach",
        "logic_signature": {{
            "input_types": "Expected input types/constraints",
            "output_types": "Expected output types",
            "state_transitions": "State changes if applicable"
        }},
        "evidence": "Quote or reference supporting the algorithm inference"
    }},
    "evidence_tracking": {{
        "technical_facts": ["List of technical facts with evidence citations"],
        "information_gaps": ["List of missing information that would be useful"],
        "confidence_level": "Overall confidence: High/Medium/Low"
    }}
}}

CRITICAL: DO NOT infer technologies not explicitly mentioned. If you see 'go' in a list, it might mean 'go to website', not 'Golang'. Only include technologies with clear evidence.

Respond ONLY with valid JSON, no additional text.""",

    "STEP2_LOGIC_ABSTRACTION": """You are a Technical Architect performing Logic Abstraction with EVIDENCE-BASED inference.

TWO-PASS REASONING REQUIRED:

PASS 1: Technical Audit
- List ONLY explicit technical facts from Step 1
- Cite evidence for each fact
- Identify information gaps

PASS 2: Abstraction
- Map facts to Logic Archetype (choose from strict list)
- Identify Core Algorithmic Class
- Assess Repurposing Confidence (1-10)

FORBIDDEN:
- Inferring technologies not in Step 1 evidence
- Making claims without evidence quotes
- Using marketing language
- Hallucinating technical details

REQUIRED:
- Every claim must have: Claim + Evidence + Confidence
- Use strict schema fields only

Product Analysis:
{analysis_json}

Evidence Tracking:
{evidence_json}

Provide a JSON response with this STRICT structure:
{{
    "functional_dna": {{
        "logic_archetype": "MUST choose from: Stream Processor, Batch Optimizer, Stateful Orchestrator, Stateless Transformer, Matching Engine, Search/Index Engine, Recommendation Engine, Authentication/Authorization Service, Data Aggregator, API Gateway",
        "logic_archetype_evidence": "Quote or reference supporting this choice",
        "data_contract_strictness": "Highly Structured / Moderately Structured / Schema-less / Unknown",
        "data_contract_evidence": "Evidence for contract strictness",
        "core_algorithmic_class": "Graph Algorithms / Combinatorial Optimization / Time-Series Processing / Linear Algebra / Distributed Consensus / Search Algorithms / Statistical Models / Neural Networks / CRUD Operations / Unknown",
        "core_algorithmic_evidence": "Evidence for algorithmic class",
        "concurrency_requirements": "ACID Compliance Required / Eventually Consistent / No Consistency Requirements / Unknown",
        "concurrency_evidence": "Evidence for concurrency requirements",
        "repurposing_confidence": 1-10,
        "repurposing_reasoning": "Why this confidence score? What makes it reusable or domain-specific?"
    }},
    "evidence_claims": [
        {{
            "claim": "Technical statement",
            "evidence": "Quote or reference from Step 1",
            "confidence": "High/Medium/Low"
        }}
    ],
    "market_reach": {{
        "primary_industry": "Current industry",
        "cross_industry_applications": ["List of broader industry categories"],
        "utility_score": 1-10,
        "market_potential": "High/Medium/Low"
    }},
    "friction_report": {{
        "difficulty": "Low/Medium/High",
        "estimated_hours": int,
        "required_technologies": ["List with evidence"],
        "complexity_factors": ["List"],
        "risk_level": "Low/Medium/High"
    }},
    "interface_map": {{
        "adapter_schema": {{
            "input": {{"format": "JSON", "required_fields": []}},
            "output": {{"format": "JSON"}},
            "authentication": {{"type": "...", "method": "..."}}
        }},
        "standardization_level": "High/Medium/Low"
    }},
    "information_gaps": ["List of missing information that would improve analysis"]
}}

Respond ONLY with valid JSON, no additional text.""",
}


# ============================================================================
# DEPLOYMENT OPTIONS
# ============================================================================
# Standard deployment models/options for categorizing how products are deployed.

DEPLOYMENT_OPTIONS: List[str] = [
    "SaaS",
    "On-premise",
    "Hybrid",
    "Self-hosted",
    "Cloud",
    "Unknown",
]


# ============================================================================
# PRICING MODELS
# ============================================================================
# Standard pricing model categories for products.

PRICING_MODELS: List[str] = [
    "freemium",
    "subscription",
    "one-time",
    "usage-based",
    "enterprise",
    "free",
    "unknown",
]


# ============================================================================
# DOCUMENTATION INDICATORS
# ============================================================================
# URL path patterns that indicate documentation or API reference pages.
# Used by web_scraping.py to identify docs pages during crawling.

DOCS_INDICATORS: List[str] = [
    "/docs", "/documentation", "/api", "/reference",
    "/guide", "/tutorial", "/manual", "/sdk",
    "/developer", "/getting-started",
]


# ============================================================================
# INFRASTRUCTURE KEYWORDS
# ============================================================================
# Keywords for identifying infrastructure dependencies in tech stacks.
# Used by _extract_dependencies() in generalizer.py.

INFRASTRUCTURE_KEYWORDS: Dict[str, List[str]] = {
    "database": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch"],
    "message_queue": ["kafka", "rabbitmq", "sqs", "pubsub"],
    "cache": ["redis", "memcached"],
    "cloud": ["aws", "azure", "gcp"],
    "container": ["docker", "kubernetes"],
}


# ============================================================================
# RUNTIME KEYWORDS
# ============================================================================
# Keywords identifying runtime/language dependencies.
# Used by _extract_dependencies() in generalizer.py.

RUNTIME_KEYWORDS: List[str] = [
    "python", "node", "java", "go", "rust", "ruby", "php", "javascript"
]
