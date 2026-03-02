# SynchroB

**AI-Powered Integration Engine for B2B Software Solutions**

SynchroB transforms the complex process of evaluating and integrating third-party software modules into an automated, intelligent workflow. It extracts the mathematical essence of products, strips away marketing noise, and creates functional fingerprints that enable cross-industry technology matching.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🎯 Overview

SynchroB solves the "buying vs. building" dilemma by:

- **Extracting Technical DNA**: Analyzes products to understand what they actually do, not what they claim to do
- **Evidence-Based Analysis**: Requires explicit evidence for all technical claims, preventing hallucination
- **Cross-Industry Generalization**: Identifies that a "Trading Platform" is actually a "Real-time State Synchronization Engine" usable in IoT, collaborative editing, and more
- **Automated Integration Roadmaps**: Generates compatibility scores and integration blueprints

### The Problem

When evaluating software solutions, you're often faced with:
- Marketing noise that obscures technical reality
- Hidden dependencies and architectural constraints
- Difficulty matching buyer needs with seller capabilities
- Manual, time-consuming integration planning

### The Solution

SynchroB uses AI-powered analysis to:
1. **Extract** the mathematical/structural essence of products
2. **Generalize** technical logic into reusable patterns
3. **Match** buyer requirements with seller solutions (coming in Step 3)

---

## 🏗️ Architecture

SynchroB operates in three stages:

### Step 1: Product Analysis & Technical Extraction ✅

**Intelligent web scraping and technical DNA extraction**

- **Targeted Ingestion**: Prioritizes developer artifacts (OpenAPI specs, `/docs`, `/api`) over marketing pages
- **De-Marketing Filter**: Strips marketing superlatives, focuses on functional verbs and technical nouns
- **Evidence-Based Inference**: Every technical claim includes source citations and confidence levels
- **Comprehensive Extraction**:
  - API endpoints (standardized to OpenAPI fragments)
  - Technical stack and dependencies
  - Core algorithmic patterns
  - Complexity analysis
  - Input/output contracts

**Output**: Structured JSON with technical DNA, API specifications, and evidence-backed claims.

### Step 2: Generalization & Schema Mapping ✅

**Transforms product-specific logic into reusable abstract patterns**

- **Technical DNA Schema**: Enforces strict logic archetypes (Stream Processor, Batch Optimizer, Stateful Orchestrator, etc.)
- **Two-Pass Reasoning**:
  - **Pass 1**: Technical audit (explicit facts only)
  - **Pass 2**: Abstraction (map to general problem domains)
- **Cross-Industry Mapping**: Identifies repurposing opportunities across industries
- **Integration Friction Assessment**: Estimates implementation difficulty and risk

**Output**: Functional fingerprint with market reach analysis and integration complexity scoring.

### Step 3: Matching & Integration Roadmap 🚧 (Coming Soon)

- Match buyer architectural constraints with seller solutions
- Generate compatibility scores
- Provide automated code snippets for integration bridges

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip package manager
- API keys for:
  - [Firecrawl](https://firecrawl.dev) (required)
  - [OpenAI](https://platform.openai.com) or [Google Gemini](https://makersuite.google.com/app/apikey) (optional, for LLM-based analysis)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yonatanarbel17/SynchroB.git
cd SynchroB
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure API keys:**

Create a `.env` file in the project root:

```bash
# Required
FIRECRAWL_API_KEY=your_firecrawl_key_here

# Optional (for LLM-based analysis)
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
```

> **Note**: The `.env` file is gitignored and will never be committed to the repository.

---

## 📖 Usage

### Step 1: Analyze a Product

**Basic usage** (uses intelligent pattern matching, no API calls):
```bash
python step1_cli.py https://example.com/product
```

**With LLM analysis** (for deeper insights):
```bash
python step1_cli.py https://example.com/product --use-llm
```

**Advanced options:**
```bash
# Use GPT-4 instead of Gemini
python step1_cli.py https://example.com/product --use-llm --use-gpt4

# Crawl linked pages (docs, API, etc.)
python step1_cli.py https://example.com/product --crawl-depth 2

# Output as JSON for programmatic use
python step1_cli.py https://example.com/product -f json -o analysis.json
```

**Example:**
```bash
python step1_cli.py https://www.etoro.com --crawl-depth 2 --use-llm
```

### Step 2: Generalize Product Logic

**Basic usage** (uses intelligent pattern matching):
```bash
python step2_cli.py outputs/etoro_step1.json
```

**With LLM generalization** (for deeper abstraction):
```bash
python step2_cli.py outputs/etoro_step1.json --use-llm
```

**Output formats:**
```bash
# Markdown report (default)
python step2_cli.py outputs/etoro_step1.json -f markdown

# JSON for programmatic use
python step2_cli.py outputs/etoro_step1.json -f json -o generalization.json
```

### Python API

```python
from src.step1 import Step1Processor
from src.step2 import Step2Generalizer

# Step 1: Analyze a product
processor = Step1Processor(use_llm=False)  # or use_llm=True for LLM analysis
result = processor.analyze_product("https://example.com/product", crawl_depth=2)

# Step 2: Generalize the product
generalizer = Step2Generalizer(use_llm=False)  # or use_llm=True
generalization = generalizer.generalize_product(result)

# Access results
print(generalization['generalization']['functional_dna']['abstract_problem'])
print(generalization['generalization']['market_reach']['utility_score'])
```

---

## 📊 Output Examples

### Step 1 Output Structure

```json
{
  "url": "https://example.com/product",
  "timestamp": "2024-01-01T12:00:00",
  "extracted_data": {
    "title": "Product Name",
    "api_endpoints_raw": ["GET /api/v1/users", "POST /api/v1/orders"],
    "tech_stack_mentions": ["Python", "PostgreSQL", "Redis"]
  },
  "analysis": {
    "summary": "Technical summary...",
    "capabilities": ["capability1", "capability2"],
    "technical_stack": ["tech1", "tech2"],
    "api_spec": {
      "openapi": "3.0.0",
      "paths": { ... }
    },
    "underlying_algorithm": {
      "problem_type": "Real-time Order Matching Engine",
      "complexity": "O(n log n)",
      "pattern": "Order Matching Algorithm"
    }
  }
}
```

### Step 2 Output Structure

```json
{
  "generalization": {
    "functional_dna": {
      "logic_archetype": "Stateful Orchestrator",
      "core_algorithmic_class": "Graph Traversal",
      "data_contract_strictness": "Highly Structured",
      "concurrency_requirements": "ACID",
      "repurposing_confidence": 8,
      "abstract_problem": "Real-time State Synchronization Engine",
      "complexity": "O(n log n)",
      "evidence_claims": [
        {
          "claim": "Uses order matching algorithm",
          "evidence": "Found in /docs/api: 'order matching engine'",
          "confidence": "High"
        }
      ]
    },
    "market_reach": {
      "utility_score": 8,
      "potential_industries": ["IoT", "Collaborative Software", "Financial Services"],
      "market_potential": "High"
    },
    "friction_report": {
      "difficulty": "Medium",
      "estimated_hours": 40,
      "risk_level": "Low"
    }
  }
}
```

---

## 🔧 Project Structure

```
SynchroB/
├── README.md
├── requirements.txt
├── config.py
├── step1_cli.py          # Step 1 command-line interface
├── step2_cli.py          # Step 2 command-line interface
├── src/
│   ├── ingestion/        # Web scraping (Firecrawl)
│   ├── step1/            # Product analysis
│   │   ├── processor.py
│   │   └── analysis_strategy.py
│   ├── step2/            # Generalization
│   │   ├── generalizer.py
│   │   └── generalization_strategy.py
│   └── analysis/         # LLM clients (OpenAI, Gemini)
├── guidelines/
│   └── technical_extraction_guidelines.md
└── outputs/              # Generated analysis files
```

---

## 🎓 Key Features

### Evidence-Based Analysis
- Every technical claim includes source citations
- Confidence levels (High/Medium/Low) for all inferences
- Prevents hallucination by requiring explicit evidence

### De-Marketing Filter
- Strips marketing superlatives ("powerful", "revolutionary", etc.)
- Focuses on functional verbs and technical nouns
- Prioritizes developer artifacts over marketing pages

### Technical DNA Schema
- Strict logic archetypes (Stream Processor, Batch Optimizer, etc.)
- Core algorithmic classification
- Data contract strictness analysis
- Concurrency requirements assessment

### Flexible LLM Integration
- **Default**: Intelligent pattern matching (no API calls, fast, free)
- **Optional**: LLM-based analysis (GPT-4 or Gemini) for deeper insights
- Easy switching between strategies

---

## 🛠️ Technologies

- **Python 3.10+**: Core language
- **Firecrawl**: Web scraping and content extraction
- **OpenAI API / Google Gemini**: LLM-based analysis (optional)
- **Tree-sitter**: Multi-language code parsing
- **NetworkX**: Graph processing
- **PyTorch Geometric**: Graph Neural Networks (for future Step 3)

---

## 📝 Development Status

- ✅ **Step 1**: Product Analysis & Technical Extraction (Complete)
- ✅ **Step 2**: Generalization & Schema Mapping (Complete)
- 🚧 **Step 3**: Matching & Integration Roadmap (In Progress)

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **Repository**: [https://github.com/yonatanarbel17/SynchroB](https://github.com/yonatanarbel17/SynchroB)
- **Firecrawl**: [https://firecrawl.dev](https://firecrawl.dev)
- **OpenAI**: [https://platform.openai.com](https://platform.openai.com)
- **Google Gemini**: [https://makersuite.google.com](https://makersuite.google.com)

---

## 📧 Contact

For questions, issues, or contributions, please open an issue on GitHub.

---

**Built with ❤️ for the B2B software integration ecosystem**
