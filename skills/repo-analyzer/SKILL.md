---
name: repo-analyzer
description: >
  Deep technical analysis of cloned open-source repositories. Use this skill whenever the user
  wants to analyze a GitHub repo, understand a codebase's architecture, extract the technical DNA
  of an open-source project, or run SynchroB batch analysis on a list of repos. Triggers on:
  cloned repos, local code analysis, "analyze this repo", batch GitHub analysis, codebase review,
  open-source company analysis. Even if the user just pastes a GitHub URL and says "analyze this",
  use this skill.
---

# Repo Analyzer

You are performing deep technical analysis of a cloned source code repository. Your job is to
extract the **functional truth** of what this codebase does — its architecture, algorithms,
data flow, dependencies, and integration surface — by reading actual source code, not marketing
copy.

This is fundamentally different from analyzing a product website. You have the source of truth
in front of you: the code itself. Every claim you make should be grounded in a specific file
and line you observed.

## How You Receive Input

You will be given a structured extraction of a cloned repo, produced by `scripts/extract_repo_structure.py`. It contains:

1. **Directory structure** — a 3-level deep tree showing project organization
2. **File tree** — every file path in the repo (may be truncated for large repos)
3. **Language distribution** — file counts by extension
4. **README content** — the project's own description
5. **Architecture/design docs** — CONTRIBUTING.md, ARCHITECTURE.md, DESIGN.md if present
6. **Dependency manifests** — parsed contents of package.json, requirements.txt, go.mod, etc.
7. **OpenAPI/Swagger specs** — if found on disk, the full parsed spec
8. **Source code samples** — entry points, route definitions, models, core modules
9. **Configuration files** — Docker, CI/CD, env templates
10. **Database schemas** — migration files, ORM models, SQL schemas
11. **Test info** — test file counts, frameworks, sample paths
12. **Git metadata** — recent commits, top contributors, repo age, commit count
13. **Plugin/extension system** — plugin directories, hook patterns
14. **License** — detected license type
15. **Community health** — code of conduct, security policy, templates

## What You Extract

Produce a single JSON object with this structure. Every field matters — SynchroB's Step 2
generalization pipeline consumes this output directly. Be THOROUGH — aim for 15-25 capabilities,
detailed architecture analysis, and comprehensive evidence.

```json
{
  "summary": "3-5 sentence technical description of what the system does, its primary architecture pattern, and what makes it technically distinctive. Use functional verbs (processes, transforms, routes, matches). No marketing language.",

  "capabilities": [
    "IMPORTANT: List 15-25 specific technical capabilities with file evidence.",
    "Each should describe a distinct function the code performs.",
    "e.g., 'Processes incoming webhook events and dispatches to handler functions (src/webhooks/dispatcher.py)'",
    "e.g., 'Implements incremental tree-sitter parsing for real-time syntax highlighting (src/highlight/incremental.rs)'",
    "e.g., 'Manages database connection pooling with configurable pool size and health checks (src/db/pool.py)'"
  ],

  "use_cases": [
    "Who uses this software and for what purpose.",
    "e.g., 'DevOps teams use this to monitor application performance and set alerting thresholds'",
    "e.g., 'Data engineers use this to build ETL pipelines with exactly-once delivery guarantees'"
  ],

  "category": "The primary domain: Text Editor, Database Engine, Web Framework, E-commerce Platform, Monitoring System, etc. Be specific, not 'Open Source Software'.",

  "target_audience": "Specific audience: Backend developers, Data scientists, DevOps engineers, System administrators, etc.",

  "technical_stack": [
    "Only technologies you can confirm from dependency files or import statements.",
    "Include version numbers when available.",
    "e.g., 'FastAPI 0.104.1 (requirements.txt)', 'PostgreSQL 15 (docker-compose.yml, SQLAlchemy models in src/db/)'"
  ],

  "api_endpoints": [
    "Extracted from route definitions in the code or OpenAPI specs.",
    "For non-HTTP APIs (RPC, CLI, library APIs), list the public interface methods.",
    "Format: 'METHOD /path — description (source_file:line)' or 'function_name(params) — description (source_file)'"
  ],

  "sdk_languages": ["Languages the project provides client libraries for, with evidence"],

  "auth_methods": ["Authentication mechanisms found in the code (JWT, OAuth2, API keys, RBAC, SAML, etc.) with file evidence"],

  "integrations": [
    "External services the code connects to, with evidence from imports/configs.",
    "e.g., 'PostgreSQL via SQLAlchemy (src/db/session.py imports sqlalchemy)',",
    "e.g., 'AWS S3 for file storage (src/storage/s3.py imports boto3)',",
    "e.g., 'Redis for caching and pub/sub (docker-compose.yml, src/cache/redis_client.py)'"
  ],

  "architecture": {
    "pattern": "monolith / microservices / serverless / library / CLI tool / framework / plugin-based / monorepo with multiple services",
    "components": ["Major architectural components/modules and their responsibilities"],
    "entry_points": ["Main entry point files (e.g., main.py, index.ts, cmd/server/main.go)"],
    "data_flow": "Detailed description of how data moves through the system — from input to processing to storage to output",
    "persistence": "What databases/storage the code uses, ORM layer, migration strategy",
    "concurrency_model": "sync / async / multi-threaded / actor-based / goroutines / event-loop, with evidence",
    "communication_patterns": "HTTP REST / gRPC / WebSocket / message queue / RPC — how components talk to each other",
    "plugin_extension_model": "How the system supports plugins/extensions/middleware, if applicable"
  },

  "data_model": {
    "primary_entities": ["Core domain objects/models the system manages"],
    "storage_backends": ["Databases, file systems, caches used"],
    "schema_patterns": "How data is structured — relational, document, graph, key-value, etc.",
    "migration_strategy": "How schema changes are managed (Alembic, Flyway, Rails migrations, etc.)"
  },

  "algorithms": {
    "problem_type": "The abstract computational problem being solved (e.g., 'Text editing with incremental parsing', 'Distributed consensus', 'Real-time stream processing')",
    "core_patterns": ["Design patterns observed in the code (Repository, Observer, Strategy, Plugin, Event Sourcing, CQRS, etc.)"],
    "complexity_indicators": "Observable complexity characteristics with evidence",
    "key_algorithms": ["Specific algorithms used: B-tree indexing, Raft consensus, CRDT merge, etc. with file evidence"],
    "evidence": "Specific files/functions that demonstrate the core algorithm"
  },

  "security_model": {
    "authentication": "How users are authenticated",
    "authorization": "How permissions are enforced (RBAC, ABAC, ACL, etc.)",
    "data_protection": "Encryption at rest/transit, secret management",
    "security_headers": "CSP, CORS, rate limiting if applicable",
    "vulnerability_handling": "SECURITY.md, dependency scanning, etc."
  },

  "dependencies": {
    "runtime": ["Direct runtime dependencies from manifests with versions"],
    "dev": ["Dev/test dependencies"],
    "infrastructure": ["Required infrastructure (databases, message queues, caches, object storage)"]
  },

  "deployment": {
    "containerized": true/false,
    "container_orchestration": "Docker Compose / Kubernetes / ECS / none",
    "ci_cd": "GitHub Actions / GitLab CI / Jenkins / none observed",
    "environment_config": "How the app is configured (env vars, config files, feature flags, etc.)",
    "scaling_model": "Horizontal / vertical / auto-scaling signals"
  },

  "code_quality_signals": {
    "has_tests": true/false,
    "test_framework": "pytest / jest / go test / JUnit / etc.",
    "test_count_estimate": "Number of test files found",
    "has_linting": true/false,
    "has_type_hints": true/false,
    "documentation_quality": "well-documented / adequate / sparse / none",
    "code_style": "What style enforcement exists (prettier, black, gofmt, etc.)"
  },

  "project_health": {
    "license": "MIT / Apache-2.0 / GPL-3.0 / etc.",
    "total_commits": "Number from git history",
    "top_contributors": "Number of significant contributors",
    "recent_activity": "Summary of what recent commits show about project direction",
    "community_signals": "Issue templates, PR templates, code of conduct, security policy"
  },

  "evidence_tracking": {
    "files_analyzed": ["List of key files you read to form your analysis"],
    "confidence_level": "High / Medium / Low",
    "information_gaps": ["Things you couldn't determine from the code alone"]
  }
}
```

## Analysis Strategy

Work through the repo extraction in this order. Each phase builds on the previous one.

### Phase 1: Orientation (30 seconds)
Read the directory structure, file tree, and README first. Form a hypothesis about what this
project does, what language ecosystem it's in, and roughly how it's structured.

### Phase 2: Architecture Deep-Dive
Read the directory structure tree (3-level), architecture docs (CONTRIBUTING.md, ARCHITECTURE.md),
and source code samples. Map out the major components, how they communicate, and where the
boundaries are. Look for monorepo signals (multiple package.json or go.mod files).

### Phase 3: Dependency Truth
Parse the dependency manifests. These are the most reliable signal for technical stack — if
`requirements.txt` lists `fastapi` and `sqlalchemy`, that's HIGH confidence. Include version
numbers when visible. Don't guess technologies from variable names or comments.

### Phase 4: Deep Code Reading
Read ALL source code samples provided. Focus on:
- **Route/handler definitions** → API endpoints and communication patterns
- **Model/schema definitions** → data model and persistence layer
- **Service/business logic** → core algorithms, design patterns, capabilities
- **Authentication/authorization** → security model
- **Configuration loading** → deployment and environment model
- **Plugin/hook systems** → extension architecture
- **Error handling patterns** → resilience and recovery strategy

### Phase 5: Data Model Analysis
From database schemas, migration files, and ORM models, reconstruct the data model.
Identify primary entities, relationships, and storage patterns.

### Phase 6: Quality & Health Assessment
Use test info, git metadata, community health signals, and documentation presence to
assess project maturity. Recent commit patterns reveal project direction and health.

### Phase 7: Synthesis
Combine everything into the output JSON. For every claim, ask yourself: "Which file did I see
this in?" If you can't point to a file, either mark the confidence as Low or omit the claim.

**AIM FOR COMPLETENESS**: A good analysis has 15-25 capabilities, 3-5 use cases, detailed
architecture with all subfields filled, a complete data model section, and thorough evidence
tracking. If you're producing fewer than 15 capabilities, you're not reading deeply enough.

## Rules

- **Evidence over inference.** If you see `import redis` in the code, that's evidence of Redis
  usage. If the README says "blazing fast caching", that is not evidence of anything specific.
- **Strip marketing from READMEs.** READMEs mix technical facts with aspirational language.
  Extract the technical substance. Ignore superlatives.
- **Don't hallucinate endpoints.** Only list API endpoints you can see defined in route files
  or OpenAPI specs. "The code probably has a /users endpoint" is not acceptable.
- **Dependency files are canonical.** If `package.json` says `"express": "^4.18.0"`, that's
  a fact. If a comment says "we're migrating to Fastify", it's a maybe — note it in
  information_gaps but don't list Fastify as part of the stack.
- **Category must be specific.** "Open Source Software" is never an acceptable category. Every
  project has a specific domain: Text Editor, Database Engine, CI/CD Platform, etc.
- **Use cases must be concrete.** "Developers use it" is not useful. "Backend developers use it
  to build REST APIs with auto-generated OpenAPI docs" is useful.
- **One repo = one analysis.** Even if the repo is a monorepo with multiple services, produce
  a single unified analysis that covers the whole thing. Note the monorepo structure in
  the architecture section.
- **Fill every field.** If you genuinely cannot determine something, use null or an empty array
  with a note in information_gaps. But try hard — most fields can be filled from the extraction.
