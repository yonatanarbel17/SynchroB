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

1. **File tree** — every file path in the repo
2. **Dependency manifests** — parsed contents of `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, etc.
3. **README content** — the project's own description
4. **OpenAPI/Swagger specs** — if found on disk, the full parsed spec
5. **Source code samples** — entry points, route definitions, core modules (truncated to fit context)
6. **Configuration files** — Docker, CI/CD, env templates

## What You Extract

Produce a single JSON object with this structure. Every field matters — SynchroB's Step 2
generalization pipeline consumes this output directly.

```json
{
  "summary": "2-3 sentence technical description of what the system does. Use functional verbs (processes, transforms, routes, matches). No marketing language.",

  "capabilities": [
    "Each capability is a specific technical function the code performs, with file evidence.",
    "e.g., 'Processes incoming webhook events and dispatches to handler functions (src/webhooks/dispatcher.py)'"
  ],

  "category": "The primary domain: API Gateway, Data Pipeline, Authentication Service, etc.",

  "technical_stack": [
    "Only technologies you can confirm from dependency files or import statements.",
    "e.g., 'FastAPI (requirements.txt)', 'PostgreSQL (docker-compose.yml, SQLAlchemy models in src/db/)'"
  ],

  "api_endpoints": [
    "Extracted from route definitions in the code or OpenAPI specs.",
    "Format: 'METHOD /path — description (source_file:line)'"
  ],

  "sdk_languages": ["Languages the project provides client libraries for"],

  "auth_methods": ["Authentication mechanisms found in the code (JWT, OAuth2, API keys, etc.)"],

  "integrations": ["External services the code connects to, with evidence from imports/configs"],

  "architecture": {
    "pattern": "monolith / microservices / serverless / library / CLI tool / framework",
    "entry_points": ["Main entry point files (e.g., main.py, index.ts, cmd/server/main.go)"],
    "data_flow": "Brief description of how data moves through the system",
    "persistence": "What databases/storage the code uses and how",
    "concurrency_model": "sync / async / multi-threaded / actor-based / goroutines, with evidence"
  },

  "algorithms": {
    "problem_type": "The abstract computational problem being solved",
    "core_patterns": ["Design patterns observed in the code (Repository, Observer, Strategy, etc.)"],
    "complexity_indicators": "Any observable complexity characteristics (e.g., nested loops over large datasets, recursive graph traversal)",
    "evidence": "Specific files/functions that demonstrate the core algorithm"
  },

  "dependencies": {
    "runtime": ["Direct runtime dependencies from manifests"],
    "dev": ["Dev/test dependencies"],
    "infrastructure": ["Required infrastructure (databases, message queues, caches)"]
  },

  "deployment": {
    "containerized": true/false,
    "ci_cd": "GitHub Actions / GitLab CI / Jenkins / none observed",
    "environment_config": "How the app is configured (env vars, config files, etc.)"
  },

  "code_quality_signals": {
    "has_tests": true/false,
    "test_framework": "pytest / jest / go test / etc.",
    "has_linting": true/false,
    "has_type_hints": true/false,
    "documentation_quality": "well-documented / sparse / none"
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

### Phase 1: Orientation
Read the file tree and README first. Form a hypothesis about what this project does, what
language ecosystem it's in, and roughly how it's structured. This takes 30 seconds of thought
and saves you from misinterpreting code later.

### Phase 2: Dependency Truth
Parse the dependency manifests. These are the most reliable signal for technical stack — if
`requirements.txt` lists `fastapi` and `sqlalchemy`, that's HIGH confidence that the project
uses FastAPI and SQLAlchemy. Don't guess technologies from variable names or comments.

### Phase 3: Architecture Mapping
Look at entry points, directory structure, and how modules import each other. Identify:
- Where requests enter the system (routes, handlers, CLI commands)
- Where data is stored (database models, file I/O)
- Where external calls go out (HTTP clients, SDK usage, message publishing)

### Phase 4: Deep Code Reading
Read the source code samples. Focus on:
- **Route/handler definitions** → API endpoints
- **Model/schema definitions** → data contracts
- **Service/business logic** → core algorithms and capabilities
- **Authentication middleware** → auth methods
- **Configuration loading** → deployment model

### Phase 5: Synthesis
Combine everything into the output JSON. For every claim, ask yourself: "Which file did I see
this in?" If you can't point to a file, either mark the confidence as Low or omit the claim.

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
- **One repo = one analysis.** Even if the repo is a monorepo with multiple services, produce
  a single unified analysis that covers the whole thing. Note the monorepo structure in
  the architecture section.
