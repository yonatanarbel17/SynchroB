# Technical Extraction Guidelines for SynchroB

## Core Principle: Evidence-Based Logic Extraction

**Goal**: Extract the **mathematical/structural essence** of a product, not its marketing description.

---

## Step 1: Targeted Ingestion Guidelines

### Priority Order for Content Sources

1. **Developer Artifacts (90% weight)**
   - OpenAPI/Swagger specifications
   - API documentation (`/docs`, `/api`, `/developers`)
   - GitHub repositories (if public)
   - NPM/PyPI package metadata
   - SDK documentation

2. **Technical Documentation (70% weight)**
   - Architecture diagrams
   - Technical blog posts (not marketing)
   - Integration guides
   - Developer tutorials

3. **Landing Page (10% weight)**
   - Only extract factual claims (e.g., "supports 1000 requests/second")
   - Ignore marketing superlatives

### De-Marketing Filter

**Strip these words/phrases:**
- Marketing superlatives: "powerful", "easy-to-use", "revolutionary", "cutting-edge", "best-in-class"
- User testimonials and social proof
- Pricing/marketing copy
- Feature lists without technical details

**Keep these:**
- Functional verbs: "processes", "transforms", "validates", "synchronizes"
- Technical nouns: "API endpoints", "message queue", "database schema", "authentication tokens"
- Quantitative claims: "handles 10M requests/day", "99.9% uptime", "sub-100ms latency"
- Architecture patterns: "microservices", "event-driven", "RESTful", "GraphQL"

### Evidence Requirements

Every technical claim MUST include:
- **Source**: Where was this found? (e.g., "OpenAPI spec at /api/v1/swagger.json")
- **Confidence**: High (explicitly stated), Medium (inferred from structure), Low (speculative)

---

## Step 2: Technical DNA Schema (Strict)

### Required Fields

#### 1. Logic Archetype (MUST choose from list)
- **Stream Processor**: Real-time event processing (Kafka, event streams)
- **Batch Optimizer**: Scheduled/batch data processing
- **Stateful Orchestrator**: Manages complex state transitions (workflows, state machines)
- **Stateless Transformer**: Request-response, no persistent state
- **Matching Engine**: Real-time matching algorithms (orders, resources, users)
- **Search/Index Engine**: Information retrieval and indexing
- **Recommendation Engine**: Collaborative filtering, ML-based suggestions
- **Authentication/Authorization Service**: Identity management
- **Data Aggregator**: Collects and combines data from multiple sources
- **API Gateway**: Routes and transforms API requests

#### 2. Data Contract Strictness
- **Highly Structured**: Strict schema (OpenAPI, GraphQL schema, Protobuf)
- **Moderately Structured**: JSON with documented fields but flexible
- **Schema-less**: Accepts arbitrary data structures
- **Unknown**: No API documentation found

#### 3. Core Algorithmic Class
- **Graph Algorithms**: Traversal, shortest path, network analysis
- **Combinatorial Optimization**: Matching, assignment, scheduling
- **Time-Series Processing**: Temporal data analysis, forecasting
- **Linear Algebra**: Matrix operations, factorization
- **Distributed Consensus**: Byzantine fault tolerance, consensus algorithms
- **Search Algorithms**: Indexing, retrieval, ranking
- **Statistical Models**: Probability, Bayesian inference
- **Neural Networks**: Deep learning, ML models
- **CRUD Operations**: Standard database operations
- **Unknown**: Cannot determine from available evidence

#### 4. Concurrency Requirements
- **ACID Compliance Required**: Transactional integrity critical
- **Eventually Consistent**: Can tolerate temporary inconsistencies
- **No Consistency Requirements**: Stateless or idempotent operations
- **Unknown**: Cannot determine from evidence

#### 5. Repurposing Confidence (1-10)
- **10**: Pure algorithmic logic, no domain-specific constraints
- **7-9**: Domain-agnostic with minor adaptations needed
- **4-6**: Some domain-specific logic but core is reusable
- **1-3**: Highly domain-specific, limited reusability

### Evidence-Based Inference Rules

#### Rule 1: No Hallucination
- **FORBIDDEN**: Inferring technologies not mentioned in Step 1 data
- **REQUIRED**: Every technical claim must cite evidence from Step 1

#### Rule 2: Evidence Quotes
For each technical claim, provide:
```
Claim: [Technical statement]
Evidence: [Quote or reference from Step 1 data]
Confidence: High/Medium/Low
```

#### Rule 3: Two-Pass Reasoning

**Pass 1: Technical Audit**
- Extract ONLY what is explicitly stated
- List all technical facts with sources
- Identify gaps in information

**Pass 2: Abstraction**
- Map explicit facts to Logic Archetype
- Identify mathematical essence
- Generalize to problem domain

---

## Example: eToro "CopyTrader" Analysis

### Step 1 Output (Evidence-Based)
```
Technical Facts:
- API endpoint: POST /api/v1/copy-trade
- Real-time synchronization mentioned in docs
- Supports multiple follower accounts
Evidence: Found in /docs/api-reference.md, line 45
```

### Step 2 Output (Strict Schema)
```
Logic Archetype: Stateful Orchestrator
Evidence: "Real-time synchronization" + "multiple follower accounts" → state replication pattern

Core Algorithmic Class: Time-Series Processing
Evidence: "Real-time synchronization" → temporal event stream processing

Data Contract Strictness: Moderately Structured
Evidence: JSON API with documented fields in OpenAPI spec

Repurposing Confidence: 8/10
Reasoning: State synchronization pattern is domain-agnostic. Could be used for:
- Real-time collaborative editing
- IoT sensor data replication
- Multi-master database synchronization
```

---

## Prompt Engineering Guidelines

### Step 1 Prompt Template
```
You are a Technical Documentation Extractor. Your goal is to extract ONLY technical facts.

STRIP ALL MARKETING LANGUAGE:
- Remove: "powerful", "easy", "revolutionary", "best-in-class"
- Keep: Technical specifications, API endpoints, architecture patterns

EVIDENCE REQUIREMENTS:
- Every claim must cite its source (file, URL, line number if possible)
- Mark confidence: High (explicit), Medium (inferred), Low (speculative)

PRIORITY:
1. OpenAPI/Swagger specs (weight: 90%)
2. API documentation (weight: 70%)
3. Technical docs (weight: 50%)
4. Landing page (weight: 10%)
```

### Step 2 Prompt Template
```
You are a Technical Architect performing Logic Abstraction.

TWO-PASS REASONING:

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

REQUIRED:
- Every claim must have: Claim + Evidence + Confidence
- Use strict schema fields only
```

---

## Quality Checklist

Before outputting Step 1 or Step 2, verify:

- [ ] No marketing superlatives in output
- [ ] Every technical claim has evidence citation
- [ ] Logic Archetype chosen from strict list
- [ ] Repurposing Confidence justified with reasoning
- [ ] No hallucinated technologies (e.g., "Go" without evidence)
- [ ] Two-pass reasoning clearly separated
- [ ] Gaps in information explicitly stated

---

*Last Updated: 2026-02-28*
