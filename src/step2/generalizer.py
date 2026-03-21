"""
Step 2 Generalizer: Transforms Step 1 output into context-free Functional DNA.
"""

from typing import Dict, Any, Optional
import json
import re
from datetime import datetime

from src.analysis import GeminiClient, OpenAIClient, ClaudeClient
from src.step2.generalization_strategy import (
    GeneralizationStrategy,
    DirectGeneralizationStrategy,
    GeminiGeneralizationStrategy,
    OpenAIGeneralizationStrategy,
    ClaudeGeneralizationStrategy,
)
from src.utils import setup_logger
from config import config

logger = setup_logger(__name__)


class Step2Generalizer:
    """
    Step 2: Generalization and Valuation Processor
    
    Takes Step 1 output and creates:
    - Functional DNA (abstract problem description)
    - Market Reach (potential industries)
    - Friction Report (integration complexity)
    - Interface Map (standardized adapter schema)
    """
    
    def __init__(self, generalization_strategy: Optional[GeneralizationStrategy] = None,
                 use_gemini: bool = False, use_llm: bool = False):
        """
        Initialize Step 2 generalizer.

        Args:
            generalization_strategy: Optional custom generalization strategy. If None, auto-selected.
            use_gemini: If True, prefer Gemini when use_llm=True. Default: False
            use_llm: If True, use LLM APIs for generalization. Default: False (direct analysis).

        When use_llm=True, the priority order is:
          1. Claude (Anthropic) — the default / go-to
          2. Gemini (if use_gemini=True or Claude unavailable)
          3. OpenAI (fallback)
          4. Direct analysis (final fallback)
        """
        if generalization_strategy is not None:
            self.generalization_strategy = generalization_strategy
        elif use_llm:
            self.generalization_strategy = self._init_llm_strategy(use_gemini)
        else:
            self.generalization_strategy = DirectGeneralizationStrategy(self._generate_direct_generalization)

        logger.info(f"Using generalization strategy: {self.generalization_strategy.get_name()}")

    def _init_llm_strategy(self, use_gemini: bool) -> GeneralizationStrategy:
        """Try Claude first, then Gemini/OpenAI, then direct generalization."""
        fallback = self._generate_direct_generalization

        # 1. Try Claude first (default / go-to)
        if config.ANTHROPIC_API_KEY:
            try:
                claude_client = ClaudeClient()
                return ClaudeGeneralizationStrategy(
                    fallback,
                    self._generate_llm_generalization_claude,
                    claude_client,
                )
            except Exception as e:
                logger.warning(f"Could not initialize Claude client: {e}")

        # 2. Try Gemini
        if use_gemini or config.GEMINI_API_KEY:
            try:
                gemini_client = GeminiClient()
                return GeminiGeneralizationStrategy(
                    fallback,
                    self._generate_llm_generalization_gemini,
                    gemini_client,
                )
            except Exception as e:
                logger.warning(f"Could not initialize Gemini client: {e}")

        # 3. Try OpenAI
        if config.OPENAI_API_KEY:
            try:
                openai_client = OpenAIClient()
                return OpenAIGeneralizationStrategy(
                    fallback,
                    self._generate_llm_generalization_openai,
                    openai_client,
                )
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")

        # 4. Final fallback
        logger.info("No LLM client available, using direct intelligent generalization")
        return DirectGeneralizationStrategy(fallback)
    
    def generalize_product(self, step1_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generalize a product from Step 1 output.
        
        Args:
            step1_data: Complete Step 1 output dictionary
            
        Returns:
            Dictionary containing generalization results
        """
        logger.info("Generalizing product from Step 1 data...")
        
        # Validate Step 1 data structure
        if not isinstance(step1_data, dict):
            raise ValueError("Step 1 data must be a dictionary")
        
        if "analysis" not in step1_data:
            raise ValueError("Step 1 data must contain 'analysis' field")
        
        # Generate generalization using selected strategy
        generalization = self.generalization_strategy.generalize(step1_data)
        
        # Combine with original Step 1 data
        result = {
            "step1_data": step1_data,
            "generalization": generalization,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.info("Generalization complete!")
        return result
    
    def _generate_direct_generalization(self, step1_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generalization using intelligent pattern matching."""
        analysis = step1_data.get("analysis", {})
        extracted_data = step1_data.get("extracted_data", {})
        url = step1_data.get("url", "")
        
        # 1. Logic Abstraction (strip product/industry context)
        functional_dna = self._extract_functional_dna(analysis, extracted_data)
        
        # 2. Industry Cross-Mapping
        market_reach = self._map_to_new_industries(functional_dna, analysis)
        
        # 3. Integration Complexity Assessment
        friction_report = self._estimate_integration_friction(analysis, extracted_data)
        
        # 4. Interface Standardization
        interface_map = self._create_interface_map(analysis, extracted_data)
        
        return {
            "functional_dna": functional_dna,
            "market_reach": market_reach,
            "friction_report": friction_report,
            "interface_map": interface_map,
        }
    
    def _extract_functional_dna(self, analysis: Dict[str, Any], extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract Functional DNA: Comprehensive abstract problem description without product/industry context.
        
        Returns:
            {
                "abstract_problem": "What problem does this solve?",
                "core_algorithm": "What algorithmic approach?",
                "complexity": "Time/space complexity",
                "input_output_contract": "What are the I/O constraints?",
                "state_management": "How does it handle state?",
                "scalability_pattern": "How does it scale?",
                "data_flow": "How does data flow through the system?",
                "concurrency_model": "How does it handle concurrency?",
                "error_handling": "Error handling strategy",
                "performance_characteristics": "Performance traits",
                "dependencies": "External dependencies",
                "language_agnostic_pattern": "Pattern that works across languages",
                "mathematical_model": "Underlying mathematical model if applicable"
            }
        """
        underlying_algorithm = analysis.get("underlying_algorithm", {})
        capabilities = analysis.get("capabilities", [])
        technical_stack = analysis.get("technical_stack", [])
        category = analysis.get("category", "")
        integrations = analysis.get("integrations", [])
        deployment = analysis.get("deployment", "")
        use_cases = analysis.get("use_cases", [])
        evidence_tracking = analysis.get("evidence_tracking", {})
        
        # Extract with evidence-based inference
        problem_type = underlying_algorithm.get("problem_type", "Unknown")
        pattern = underlying_algorithm.get("pattern", "Unknown")
        complexity = underlying_algorithm.get("complexity", "Unknown")
        algorithm_evidence = underlying_algorithm.get("evidence", "Inferred from content analysis")
        
        # Map to strict Logic Archetype
        logic_archetype, archetype_evidence = self._infer_logic_archetype(problem_type, capabilities, technical_stack, category)
        
        # Map to strict Core Algorithmic Class
        algorithmic_class, algorithmic_evidence = self._infer_algorithmic_class(problem_type, pattern, technical_stack)
        
        # Infer data contract strictness with evidence
        api_spec = analysis.get("api_spec")
        api_endpoints = analysis.get("api_endpoints", [])
        contract_strictness, contract_evidence = self._infer_contract_strictness(api_spec, api_endpoints, technical_stack)
        
        # Infer concurrency requirements with evidence
        concurrency_req, concurrency_evidence = self._infer_concurrency_requirements(technical_stack, capabilities, deployment)
        
        # Calculate repurposing confidence
        repurposing_confidence, repurposing_reasoning = self._calculate_repurposing_confidence(
            logic_archetype, algorithmic_class, capabilities, category
        )
        
        # Build I/O contract from API endpoints and capabilities
        api_endpoints = analysis.get("api_endpoints", [])
        api_spec = analysis.get("api_spec")
        input_output_contract = self._extract_io_contract(api_endpoints, api_spec, capabilities)
        
        # Infer state management from technical stack and capabilities
        state_management = self._infer_state_management(technical_stack, capabilities)
        
        # Infer scalability pattern
        scalability_pattern = self._infer_scalability_pattern(technical_stack, capabilities, category)
        
        # Infer data flow pattern
        data_flow = self._infer_data_flow(technical_stack, capabilities, category)
        
        # Infer concurrency model
        concurrency_model = self._infer_concurrency_model(technical_stack, capabilities, deployment)
        
        # Infer error handling strategy
        error_handling = self._infer_error_handling(technical_stack, capabilities)
        
        # Extract performance characteristics
        performance_characteristics = self._extract_performance_characteristics(complexity, technical_stack, capabilities)
        
        # Extract dependencies
        dependencies = self._extract_dependencies(technical_stack, integrations, deployment)
        
        # Extract language-agnostic pattern
        core_algorithm_value = pattern if pattern != "Unknown" else self._infer_core_algorithm(capabilities, technical_stack)
        language_agnostic_pattern = self._extract_language_agnostic_pattern(core_algorithm_value, pattern, problem_type)
        
        # Infer mathematical model
        mathematical_model = self._infer_mathematical_model(problem_type, core_algorithm_value, complexity)
        
        return {
            # Strict schema fields with evidence
            "logic_archetype": logic_archetype,
            "logic_archetype_evidence": archetype_evidence,
            "data_contract_strictness": contract_strictness,
            "data_contract_evidence": contract_evidence,
            "core_algorithmic_class": algorithmic_class,
            "core_algorithmic_evidence": algorithmic_evidence,
            "concurrency_requirements": concurrency_req,
            "concurrency_evidence": concurrency_evidence,
            "repurposing_confidence": repurposing_confidence,
            "repurposing_reasoning": repurposing_reasoning,
            # Additional technical details
            "abstract_problem": problem_type,
            "core_algorithm": pattern if pattern != "Unknown" else self._infer_core_algorithm(capabilities, technical_stack),
            "complexity": complexity,
            "input_output_contract": input_output_contract,
            "state_management": state_management,
            "scalability_pattern": scalability_pattern,
            "data_flow": data_flow,
            "concurrency_model": concurrency_model,
            "error_handling": error_handling,
            "performance_characteristics": performance_characteristics,
            "dependencies": dependencies,
            "language_agnostic_pattern": language_agnostic_pattern,
            "mathematical_model": mathematical_model,
        }
    
    def _infer_problem_type(self, capabilities: list, category: str, tech_stack: list) -> str:
        """Infer abstract problem type from capabilities and category."""
        combined_text = " ".join(capabilities).lower() + " " + category.lower() + " " + " ".join(tech_stack).lower()
        
        # Pattern matching for common problem types (order matters - more specific first)
        # Trading/Financial first (most specific)
        if any(kw in combined_text for kw in ["trading", "matching", "order", "exchange", "invest", "broker", "market"]):
            return "Real-time Order Matching / Market Making Engine"
        elif any(kw in combined_text for kw in ["payment", "transaction", "billing"]):
            return "Financial Transaction Processing / Payment Gateway"
        # Search/Indexing (check for specific search terms, not generic "search" in other contexts)
        elif any(kw in combined_text for kw in ["search engine", "full-text", "indexing", "elasticsearch", "lucene"]) and \
             not any(kw in combined_text for kw in ["trading", "invest", "financial"]):
            return "Information Retrieval / Search Indexing System"
        elif any(kw in combined_text for kw in ["recommend", "suggest", "personalize"]):
            return "Recommendation System / Collaborative Filtering"
        elif any(kw in combined_text for kw in ["stream", "event", "real-time", "kafka"]):
            return "Event Stream Processing / Real-time Data Pipeline"
        elif any(kw in combined_text for kw in ["auth", "authentication", "authorization", "sso"]):
            return "Identity & Access Management / Authentication Service"
        elif any(kw in combined_text for kw in ["api", "rest", "graphql", "endpoint"]):
            return "API Gateway / Service Integration Layer"
        elif any(kw in combined_text for kw in ["database", "storage", "persist"]):
            return "Data Persistence / Storage Abstraction Layer"
        elif any(kw in combined_text for kw in ["analytics", "metrics", "dashboard", "report"]):
            return "Data Aggregation / Analytics Pipeline"
        
        return "General Purpose Software Service"
    
    def _infer_core_algorithm(self, capabilities: list, tech_stack: list) -> str:
        """Infer core algorithmic approach."""
        combined = " ".join(capabilities).lower() + " " + " ".join(tech_stack).lower()
        
        if any(kw in combined for kw in ["graph", "node", "traversal"]):
            return "Graph Algorithm"
        elif any(kw in combined for kw in ["sort", "search", "binary"]):
            return "Sorting/Searching Algorithm"
        elif any(kw in combined for kw in ["cache", "redis", "memcached"]):
            return "Caching Strategy"
        elif any(kw in combined for kw in ["queue", "message", "pubsub"]):
            return "Message Queue / Pub-Sub Pattern"
        elif any(kw in combined for kw in ["map", "reduce", "batch"]):
            return "Map-Reduce / Batch Processing"
        
        return "Request-Response / CRUD Operations"
    
    def _infer_logic_archetype(self, problem_type: str, capabilities: list, tech_stack: list, category: str) -> tuple:
        """Infer Logic Archetype from strict list with evidence."""
        combined = f"{problem_type} {' '.join(capabilities)} {' '.join(tech_stack)} {category}".lower()
        
        # Map to strict archetypes
        if any(kw in combined for kw in ["stream", "event", "kafka", "real-time", "pipeline"]):
            return ("Stream Processor", f"Found keywords: {[kw for kw in ['stream', 'event', 'kafka'] if kw in combined]}")
        elif any(kw in combined for kw in ["batch", "scheduled", "cron", "optimizer"]):
            return ("Batch Optimizer", f"Found keywords: {[kw for kw in ['batch', 'scheduled'] if kw in combined]}")
        elif any(kw in combined for kw in ["state", "orchestrator", "workflow", "state machine"]):
            return ("Stateful Orchestrator", f"Found keywords: {[kw for kw in ['state', 'orchestrator', 'workflow'] if kw in combined]}")
        elif any(kw in combined for kw in ["matching", "order", "exchange", "match"]):
            return ("Matching Engine", f"Found keywords: {[kw for kw in ['matching', 'order', 'exchange'] if kw in combined]}")
        elif any(kw in combined for kw in ["search", "index", "elasticsearch", "lucene"]):
            return ("Search/Index Engine", f"Found keywords: {[kw for kw in ['search', 'index'] if kw in combined]}")
        elif any(kw in combined for kw in ["recommendation", "collaborative", "suggest"]):
            return ("Recommendation Engine", f"Found keywords: {[kw for kw in ['recommendation', 'collaborative'] if kw in combined]}")
        elif any(kw in combined for kw in ["auth", "authentication", "authorization", "identity"]):
            return ("Authentication/Authorization Service", f"Found keywords: {[kw for kw in ['auth', 'authentication'] if kw in combined]}")
        elif any(kw in combined for kw in ["aggregate", "collect", "combine", "aggregator"]):
            return ("Data Aggregator", f"Found keywords: {[kw for kw in ['aggregate', 'collect'] if kw in combined]}")
        elif any(kw in combined for kw in ["gateway", "route", "proxy"]):
            return ("API Gateway", f"Found keywords: {[kw for kw in ['gateway', 'route'] if kw in combined]}")
        elif any(kw in combined for kw in ["stateless", "rest", "api", "transformer"]):
            return ("Stateless Transformer", f"Found keywords: {[kw for kw in ['stateless', 'rest', 'api'] if kw in combined]}")
        
        return ("Stateless Transformer", "Default: No specific archetype identified, defaulting to stateless")
    
    def _infer_algorithmic_class(self, problem_type: str, pattern: str, tech_stack: list) -> tuple:
        """Infer Core Algorithmic Class from strict list with evidence."""
        combined = f"{problem_type} {pattern} {' '.join(tech_stack)}".lower()
        
        if any(kw in combined for kw in ["graph", "network", "traversal", "pathfinding"]):
            return ("Graph Algorithms", f"Found keywords: {[kw for kw in ['graph', 'network', 'traversal'] if kw in combined]}")
        elif any(kw in combined for kw in ["matching", "optimization", "assignment", "combinatorial"]):
            return ("Combinatorial Optimization", f"Found keywords: {[kw for kw in ['matching', 'optimization'] if kw in combined]}")
        elif any(kw in combined for kw in ["time-series", "temporal", "forecast", "stream"]):
            return ("Time-Series Processing", f"Found keywords: {[kw for kw in ['time-series', 'temporal'] if kw in combined]}")
        elif any(kw in combined for kw in ["matrix", "linear algebra", "factorization"]):
            return ("Linear Algebra", f"Found keywords: {[kw for kw in ['matrix', 'linear'] if kw in combined]}")
        elif any(kw in combined for kw in ["consensus", "byzantine", "fault tolerance", "distributed"]):
            return ("Distributed Consensus", f"Found keywords: {[kw for kw in ['consensus', 'byzantine'] if kw in combined]}")
        elif any(kw in combined for kw in ["search", "index", "retrieval", "ranking"]):
            return ("Search Algorithms", f"Found keywords: {[kw for kw in ['search', 'index'] if kw in combined]}")
        elif any(kw in combined for kw in ["statistical", "probability", "bayesian"]):
            return ("Statistical Models", f"Found keywords: {[kw for kw in ['statistical', 'probability'] if kw in combined]}")
        elif any(kw in combined for kw in ["neural", "machine learning", "deep learning", "ml"]):
            return ("Neural Networks", f"Found keywords: {[kw for kw in ['neural', 'machine learning'] if kw in combined]}")
        elif any(kw in combined for kw in ["crud", "database", "persist"]):
            return ("CRUD Operations", f"Found keywords: {[kw for kw in ['crud', 'database'] if kw in combined]}")
        
        return ("Unknown", "No clear algorithmic class identified from evidence")
    
    def _infer_contract_strictness(self, api_spec: Optional[Dict], api_endpoints: list, tech_stack: list) -> tuple:
        """Infer data contract strictness with evidence."""
        if api_spec and "paths" in api_spec:
            return ("Highly Structured", f"Found OpenAPI/Swagger spec with {len(api_spec.get('paths', {}))} paths")
        elif api_endpoints:
            return ("Moderately Structured", f"Found {len(api_endpoints)} API endpoints with documented patterns")
        elif any(tech in tech_stack for tech in ["graphql", "protobuf"]):
            return ("Highly Structured", f"Found structured API technology: {[t for t in tech_stack if t in ['graphql', 'protobuf']]}")
        
        return ("Unknown", "No API documentation or structured schema found")
    
    def _infer_concurrency_requirements(self, tech_stack: list, capabilities: list, deployment: str) -> tuple:
        """Infer concurrency requirements with evidence."""
        combined = f"{' '.join(tech_stack)} {' '.join(capabilities)}".lower()
        
        if any(kw in combined for kw in ["transaction", "acid", "atomic", "database"]):
            return ("ACID Compliance Required", f"Found keywords: {[kw for kw in ['transaction', 'acid', 'atomic'] if kw in combined]}")
        elif any(kw in combined for kw in ["eventually consistent", "cassandra", "dynamodb"]):
            return ("Eventually Consistent", f"Found keywords: {[kw for kw in ['eventually', 'cassandra'] if kw in combined]}")
        elif any(kw in combined for kw in ["stateless", "rest", "idempotent"]):
            return ("No Consistency Requirements", f"Found keywords: {[kw for kw in ['stateless', 'rest'] if kw in combined]}")
        
        return ("Unknown", "Cannot determine consistency requirements from evidence")
    
    def _calculate_repurposing_confidence(self, logic_archetype: str, algorithmic_class: str, capabilities: list, category: str) -> tuple:
        """Calculate repurposing confidence (1-10) with reasoning."""
        score = 5  # Base score
        
        # High confidence indicators
        if logic_archetype in ["Stream Processor", "Matching Engine", "Search/Index Engine"]:
            score += 3
        if algorithmic_class in ["Graph Algorithms", "Combinatorial Optimization", "Time-Series Processing"]:
            score += 2
        if len(capabilities) > 10:
            score += 1
        
        # Low confidence indicators
        if category and "specific" in category.lower():
            score -= 2
        if logic_archetype == "Authentication/Authorization Service" and "domain-specific" in str(capabilities).lower():
            score -= 1
        
        score = max(1, min(10, score))
        
        reasoning = f"Logic Archetype: {logic_archetype} ({'domain-agnostic' if score >= 7 else 'some domain specificity'}). "
        reasoning += f"Algorithmic Class: {algorithmic_class} ({'reusable' if algorithmic_class != 'CRUD Operations' else 'domain-specific'})."
        
        return (score, reasoning)
    
    def _extract_io_contract(self, api_endpoints: list, api_spec: Optional[Dict], capabilities: list) -> Dict[str, Any]:
        """Extract input/output contract from API endpoints."""
        contract = {
            "input_types": [],
            "output_types": [],
            "required_parameters": [],
            "optional_parameters": [],
        }
        
        # If we have OpenAPI spec, extract from there
        if api_spec and "paths" in api_spec:
            # Extract from OpenAPI paths
            for path, methods in api_spec["paths"].items():
                for method, details in methods.items():
                    if "parameters" in details:
                        for param in details["parameters"]:
                            param_info = {
                                "name": param.get("name", ""),
                                "type": param.get("schema", {}).get("type", "string"),
                                "required": param.get("required", False)
                            }
                            if param_info["required"]:
                                contract["required_parameters"].append(param_info)
                            else:
                                contract["optional_parameters"].append(param_info)
        
        # Infer from capabilities if no API spec
        if not contract["required_parameters"] and capabilities:
            # Generic inference
            contract["input_types"] = ["Request Object", "Configuration Parameters"]
            contract["output_types"] = ["Response Object", "Status Code"]
        
        return contract
    
    def _infer_state_management(self, tech_stack: list, capabilities: list) -> str:
        """Infer state management approach."""
        combined = " ".join(tech_stack).lower() + " " + " ".join(capabilities).lower()
        
        if any(kw in combined for kw in ["redis", "cache", "memcached"]):
            return "External Cache / Distributed State"
        elif any(kw in combined for kw in ["database", "postgresql", "mysql", "mongodb"]):
            return "Persistent Database State"
        elif any(kw in combined for kw in ["stateless", "rest", "api"]):
            return "Stateless / Request-Based"
        elif any(kw in combined for kw in ["session", "cookie", "token"]):
            return "Session-Based State Management"
        
        return "Unknown / Context-Dependent"
    
    def _infer_scalability_pattern(self, tech_stack: list, capabilities: list, category: str) -> str:
        """Infer scalability pattern."""
        combined = " ".join(tech_stack).lower() + " " + category.lower()
        
        if any(kw in combined for kw in ["kubernetes", "docker", "microservice"]):
            return "Horizontal Scaling / Microservices Architecture"
        elif any(kw in combined for kw in ["load balancer", "distributed"]):
            return "Load-Balanced / Distributed System"
        elif any(kw in combined for kw in ["queue", "async", "message"]):
            return "Asynchronous / Queue-Based Processing"
        elif any(kw in combined for kw in ["cache", "redis"]):
            return "Cache-Heavy / Read-Optimized"
        
        return "Vertical Scaling / Monolithic"
    
    def _infer_data_flow(self, tech_stack: list, capabilities: list, category: str) -> str:
        """Infer data flow pattern."""
        combined = " ".join(tech_stack).lower() + " " + " ".join(capabilities).lower() + " " + category.lower()
        
        if any(kw in combined for kw in ["stream", "kafka", "event", "pipeline"]):
            return "Event-Driven / Stream Processing"
        elif any(kw in combined for kw in ["queue", "message", "pubsub"]):
            return "Message Queue / Asynchronous Processing"
        elif any(kw in combined for kw in ["api", "rest", "graphql", "http"]):
            return "Request-Response / Synchronous API"
        elif any(kw in combined for kw in ["batch", "scheduled", "cron"]):
            return "Batch Processing / Scheduled Jobs"
        elif any(kw in combined for kw in ["websocket", "real-time", "live"]):
            return "Real-time / Bidirectional Communication"
        
        return "Request-Response / Standard HTTP"
    
    def _infer_concurrency_model(self, tech_stack: list, capabilities: list, deployment: str) -> str:
        """Infer concurrency model."""
        combined = " ".join(tech_stack).lower() + " " + " ".join(capabilities).lower()
        
        if any(kw in combined for kw in ["async", "await", "coroutine", "event loop"]):
            return "Asynchronous / Event Loop"
        elif any(kw in combined for kw in ["thread", "multithread", "parallel"]):
            return "Multi-threaded / Parallel Processing"
        elif any(kw in combined for kw in ["process", "multiprocess", "worker"]):
            return "Multi-process / Worker Pool"
        elif any(kw in combined for kw in ["actor", "akka", "erlang"]):
            return "Actor Model / Message Passing"
        elif any(kw in combined for kw in ["goroutine", "channel", "go"]):
            return "Goroutines / CSP (Communicating Sequential Processes)"
        
        return "Single-threaded / Sequential"
    
    def _infer_error_handling(self, tech_stack: list, capabilities: list) -> str:
        """Infer error handling strategy."""
        combined = " ".join(tech_stack).lower() + " " + " ".join(capabilities).lower()
        
        if any(kw in combined for kw in ["retry", "circuit breaker", "resilience"]):
            return "Resilient / Retry with Circuit Breaker"
        elif any(kw in combined for kw in ["transaction", "rollback", "atomic"]):
            return "Transactional / ACID Compliance"
        elif any(kw in combined for kw in ["queue", "dead letter", "dlq"]):
            return "Queue-Based / Dead Letter Queue"
        elif any(kw in combined for kw in ["try-catch", "exception", "error"]):
            return "Exception-Based / Try-Catch"
        
        return "Standard Error Responses / HTTP Status Codes"
    
    def _extract_performance_characteristics(self, complexity: str, tech_stack: list, capabilities: list) -> Dict[str, Any]:
        """Extract performance characteristics."""
        combined = " ".join(tech_stack).lower() + " " + " ".join(capabilities).lower()
        
        characteristics = {
            "time_complexity": complexity if complexity != "Unknown" else "Unknown",
            "space_complexity": "Unknown",
            "latency_profile": "Unknown",
            "throughput_capability": "Unknown",
            "optimization_strategies": []
        }
        
        # Infer space complexity from time complexity if available
        if "O(1)" in complexity:
            characteristics["space_complexity"] = "O(1) - Constant"
        elif "O(log n)" in complexity:
            characteristics["space_complexity"] = "O(log n) - Logarithmic"
        elif "O(n)" in complexity:
            characteristics["space_complexity"] = "O(n) - Linear"
        elif "O(n²)" in complexity or "O(n log n)" in complexity:
            characteristics["space_complexity"] = "O(n) to O(n²) - Polynomial"
        
        # Infer latency profile
        if any(kw in combined for kw in ["real-time", "low latency", "millisecond"]):
            characteristics["latency_profile"] = "Low Latency / Real-time (< 100ms)"
        elif any(kw in combined for kw in ["async", "background", "queue"]):
            characteristics["latency_profile"] = "Asynchronous / Background Processing"
        elif any(kw in combined for kw in ["batch", "scheduled"]):
            characteristics["latency_profile"] = "Batch / Scheduled Processing"
        else:
            characteristics["latency_profile"] = "Standard / Request-Response"
        
        # Infer throughput
        if any(kw in combined for kw in ["high throughput", "scalable", "distributed"]):
            characteristics["throughput_capability"] = "High Throughput / Horizontally Scalable"
        elif any(kw in combined for kw in ["cache", "redis", "optimized"]):
            characteristics["throughput_capability"] = "Cache-Optimized / Read-Heavy"
        else:
            characteristics["throughput_capability"] = "Standard / Moderate Throughput"
        
        # Extract optimization strategies
        if any(kw in combined for kw in ["cache", "redis", "memcached"]):
            characteristics["optimization_strategies"].append("Caching")
        if any(kw in combined for kw in ["index", "database index", "optimized query"]):
            characteristics["optimization_strategies"].append("Indexing")
        if any(kw in combined for kw in ["load balancer", "distributed", "sharding"]):
            characteristics["optimization_strategies"].append("Load Balancing / Distribution")
        if any(kw in combined for kw in ["compression", "gzip", "minify"]):
            characteristics["optimization_strategies"].append("Compression")
        
        return characteristics
    
    def _extract_dependencies(self, tech_stack: list, integrations: list, deployment: str) -> Dict[str, Any]:
        """Extract external dependencies."""
        dependencies = {
            "runtime_dependencies": [],
            "infrastructure_dependencies": [],
            "service_dependencies": integrations.copy() if integrations else [],
            "deployment_requirements": []
        }
        
        # Extract runtime dependencies from tech stack
        runtime_keywords = ["python", "node", "java", "go", "rust", "ruby", "php", "javascript"]
        for keyword in runtime_keywords:
            if keyword in " ".join(tech_stack).lower():
                dependencies["runtime_dependencies"].append(keyword.capitalize())
        
        # Extract infrastructure dependencies
        infra_keywords = {
            "database": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch"],
            "message_queue": ["kafka", "rabbitmq", "sqs", "pubsub"],
            "cache": ["redis", "memcached"],
            "cloud": ["aws", "azure", "gcp"],
            "container": ["docker", "kubernetes"]
        }
        
        combined_stack = " ".join(tech_stack).lower()
        for category, keywords in infra_keywords.items():
            for keyword in keywords:
                if keyword in combined_stack:
                    dependencies["infrastructure_dependencies"].append(f"{category}: {keyword}")
                    break
        
        # Extract deployment requirements
        if deployment == "SaaS":
            dependencies["deployment_requirements"] = ["Cloud Hosting", "Internet Connectivity"]
        elif deployment == "On-premise":
            dependencies["deployment_requirements"] = ["Server Infrastructure", "Network Access"]
        elif deployment == "Hybrid":
            dependencies["deployment_requirements"] = ["Cloud + On-premise Infrastructure"]
        else:
            dependencies["deployment_requirements"] = ["Standard Deployment Environment"]
        
        return dependencies
    
    def _extract_language_agnostic_pattern(self, core_algorithm: str, pattern: str, problem_type: str) -> str:
        """Extract language-agnostic design pattern."""
        combined = f"{core_algorithm} {pattern} {problem_type}".lower()
        
        # Map to well-known patterns
        if any(kw in combined for kw in ["observer", "pubsub", "event"]):
            return "Observer Pattern / Pub-Sub"
        elif any(kw in combined for kw in ["factory", "builder", "creational"]):
            return "Factory Pattern / Object Creation"
        elif any(kw in combined for kw in ["strategy", "algorithm", "policy"]):
            return "Strategy Pattern / Algorithm Selection"
        elif any(kw in combined for kw in ["adapter", "wrapper", "bridge"]):
            return "Adapter Pattern / Interface Translation"
        elif any(kw in combined for kw in ["singleton", "instance", "global"]):
            return "Singleton Pattern / Single Instance"
        elif any(kw in combined for kw in ["repository", "data access", "dao"]):
            return "Repository Pattern / Data Access Abstraction"
        elif any(kw in combined for kw in ["mvc", "mvp", "mvvm"]):
            return "MVC / MVP / MVVM Pattern"
        elif any(kw in combined for kw in ["microservice", "service", "api"]):
            return "Microservices / Service-Oriented Architecture"
        elif any(kw in combined for kw in ["map-reduce", "batch", "parallel"]):
            return "Map-Reduce / Parallel Processing"
        elif any(kw in combined for kw in ["pipeline", "chain", "workflow"]):
            return "Pipeline Pattern / Processing Chain"
        
        return "Request-Response / Standard API Pattern"
    
    def _infer_mathematical_model(self, problem_type: str, core_algorithm: str, complexity: str) -> Optional[str]:
        """Infer underlying mathematical model if applicable."""
        combined = f"{problem_type} {core_algorithm}".lower()
        
        if any(kw in combined for kw in ["graph", "network", "traversal"]):
            return "Graph Theory / Network Analysis"
        elif any(kw in combined for kw in ["matching", "optimization", "assignment"]):
            return "Combinatorial Optimization / Matching Theory"
        elif any(kw in combined for kw in ["recommendation", "collaborative", "matrix"]):
            return "Linear Algebra / Matrix Factorization"
        elif any(kw in combined for kw in ["consensus", "byzantine", "fault"]):
            return "Distributed Systems Theory / Consensus Algorithms"
        elif any(kw in combined for kw in ["search", "index", "tree"]):
            return "Tree/Graph Data Structures / Search Algorithms"
        elif any(kw in combined for kw in ["stream", "event", "time series"]):
            return "Time Series Analysis / Stream Processing"
        elif any(kw in combined for kw in ["statistical", "probability", "bayesian"]):
            return "Statistical Modeling / Probability Theory"
        elif any(kw in combined for kw in ["neural", "machine learning", "deep learning"]):
            return "Neural Networks / Deep Learning"
        
        return None
    
    def _map_to_new_industries(self, functional_dna: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map abstract problem to potential new industries/use cases.
        
        Returns:
            {
                "primary_industry": "Current industry",
                "cross_industry_applications": ["List of other industries"],
                "utility_score": 1-10,
                "market_potential": "High/Medium/Low"
            }
        """
        abstract_problem = functional_dna.get("abstract_problem", "")
        category = analysis.get("category", "")
        capabilities = analysis.get("capabilities", [])
        
        # Determine primary industry
        primary_industry = category if category else "Unknown"
        
        # Map abstract problem to cross-industry applications
        cross_industries = []
        problem_lower = abstract_problem.lower()
        
        # Pattern matching for cross-industry mapping (using broader categories)
        if "order matching" in problem_lower or "market making" in problem_lower:
            cross_industries = [
                "E-commerce & Retail",
                "Transportation & Logistics",
                "Human Resources & Recruitment",
                "Social & Networking Platforms",
                "Supply Chain & Manufacturing"
            ]
        elif "transaction processing" in problem_lower or "payment" in problem_lower:
            cross_industries = [
                "E-commerce & Retail",
                "SaaS & Cloud Services",
                "Healthcare & Life Sciences",
                "Education & E-Learning",
                "Government & Public Sector"
            ]
        elif "search" in problem_lower or "indexing" in problem_lower:
            cross_industries = [
                "E-commerce & Retail",
                "Legal & Compliance",
                "Healthcare & Life Sciences",
                "Education & E-Learning",
                "Media & Entertainment"
            ]
        elif "recommendation" in problem_lower or "collaborative filtering" in problem_lower:
            cross_industries = [
                "E-commerce & Retail",
                "Media & Entertainment",
                "Education & E-Learning",
                "Healthcare & Life Sciences",
                "Financial Services"
            ]
        elif "stream processing" in problem_lower or "event" in problem_lower:
            cross_industries = [
                "IoT & Connected Devices",
                "Financial Services",
                "Gaming & Entertainment",
                "Transportation & Logistics",
                "Security & Compliance"
            ]
        elif "authentication" in problem_lower or "identity" in problem_lower:
            cross_industries = [
                "Enterprise Software",
                "Healthcare & Life Sciences",
                "Financial Services",
                "Government & Public Sector",
                "Education & E-Learning"
            ]
        else:
            # Generic cross-industry applications (broader categories)
            cross_industries = [
                "Enterprise Software",
                "SaaS & Cloud Services",
                "B2B Integrations",
                "Internal Tools & Automation",
                "Developer Tools & Platforms"
            ]
        
        # Calculate utility score (1-10)
        utility_score = self._calculate_utility_score(functional_dna, capabilities)
        
        # Determine market potential
        if utility_score >= 8:
            market_potential = "High"
        elif utility_score >= 5:
            market_potential = "Medium"
        else:
            market_potential = "Low"
        
        return {
            "primary_industry": primary_industry,
            "cross_industry_applications": cross_industries,
            "utility_score": utility_score,
            "market_potential": market_potential,
        }
    
    def _calculate_utility_score(self, functional_dna: Dict[str, Any], capabilities: list) -> int:
        """Calculate utility score (1-10) based on how general/useful the technology is."""
        score = 5  # Base score
        
        abstract_problem = functional_dna.get("abstract_problem", "").lower()
        core_algorithm = functional_dna.get("core_algorithm", "").lower()
        
        # High utility indicators
        if any(kw in abstract_problem for kw in ["matching", "algorithm", "optimization", "processing"]):
            score += 2
        if any(kw in core_algorithm for kw in ["graph", "algorithm", "pattern", "strategy"]):
            score += 1
        if len(capabilities) > 10:
            score += 1
        
        # Low utility indicators (basic CRUD)
        if "crud" in abstract_problem.lower() or "wrapper" in abstract_problem.lower():
            score -= 2
        if len(capabilities) < 3:
            score -= 1
        
        # Clamp to 1-10
        return max(1, min(10, score))
    
    def _estimate_integration_friction(self, analysis: Dict[str, Any], extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate integration complexity and friction.
        
        Returns:
            {
                "difficulty": "Low/Medium/High",
                "estimated_hours": int,
                "required_technologies": ["List of required tech"],
                "complexity_factors": ["List of factors"],
                "risk_level": "Low/Medium/High"
            }
        """
        technical_stack = analysis.get("technical_stack", [])
        api_endpoints = analysis.get("api_endpoints", [])
        integrations = analysis.get("integrations", [])
        deployment = analysis.get("deployment", "")
        
        # Base difficulty
        difficulty = "Low"
        estimated_hours = 8  # Base: 1 day
        
        required_technologies = []
        complexity_factors = []
        
        # Assess based on technical stack
        if any(tech in technical_stack for tech in ["kubernetes", "docker", "microservice"]):
            difficulty = "High"
            estimated_hours += 40
            complexity_factors.append("Microservices architecture")
            required_technologies.extend(["Docker", "Kubernetes"])
        
        if any(tech in technical_stack for tech in ["kafka", "rabbitmq", "message queue"]):
            difficulty = "Medium"
            estimated_hours += 16
            complexity_factors.append("Message queue integration")
            required_technologies.append("Message Queue System")
        
        if any(tech in technical_stack for tech in ["redis", "cache"]):
            estimated_hours += 8
            required_technologies.append("Redis/Cache System")
        
        # Assess based on API complexity
        if len(api_endpoints) > 20:
            difficulty = "Medium" if difficulty == "Low" else "High"
            estimated_hours += 16
            complexity_factors.append("Complex API surface")
        
        if not api_endpoints:
            estimated_hours += 8
            complexity_factors.append("No public API documentation")
        
        # Assess based on integrations
        if len(integrations) > 5:
            estimated_hours += 8
            complexity_factors.append("Multiple third-party dependencies")
        
        # Assess deployment complexity
        if deployment == "On-premise":
            difficulty = "High" if difficulty == "Low" else difficulty
            estimated_hours += 24
            complexity_factors.append("On-premise deployment required")
        
        # Determine risk level
        if difficulty == "High" or estimated_hours > 80:
            risk_level = "High"
        elif difficulty == "Medium" or estimated_hours > 40:
            risk_level = "Medium"
        else:
            risk_level = "Low"
        
        return {
            "difficulty": difficulty,
            "estimated_hours": estimated_hours,
            "required_technologies": list(set(required_technologies)),
            "complexity_factors": complexity_factors,
            "risk_level": risk_level,
        }
    
    def _create_interface_map(self, analysis: Dict[str, Any], extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create standardized adapter schema/interface map.
        
        Returns:
            {
                "adapter_schema": {
                    "input": {...},
                    "output": {...},
                    "authentication": {...}
                },
                "standardization_level": "High/Medium/Low"
            }
        """
        api_endpoints = analysis.get("api_endpoints", [])
        api_spec = analysis.get("api_spec")
        technical_stack = analysis.get("technical_stack", [])
        
        adapter_schema = {
            "input": {
                "format": "JSON",
                "required_fields": [],
                "optional_fields": [],
            },
            "output": {
                "format": "JSON",
                "response_structure": {},
            },
            "authentication": {
                "type": "API Key" if "api" in " ".join(technical_stack).lower() else "Unknown",
                "method": "Bearer Token" if "oauth" in " ".join(technical_stack).lower() else "API Key",
            }
        }
        
        # If we have OpenAPI spec, use it
        if api_spec and "paths" in api_spec:
            standardization_level = "High"
            # Extract from OpenAPI spec
            for path, methods in api_spec["paths"].items():
                for method, details in methods.items():
                    if "requestBody" in details:
                        adapter_schema["input"]["required_fields"].append(f"{method.upper()} {path}")
        elif api_endpoints:
            standardization_level = "Medium"
            adapter_schema["input"]["required_fields"] = [f"Endpoint: {ep}" for ep in api_endpoints[:5]]
        else:
            standardization_level = "Low"
            adapter_schema["input"]["required_fields"] = ["Generic API Request"]
        
        return {
            "adapter_schema": adapter_schema,
            "standardization_level": standardization_level,
        }
    
    def _generate_llm_generalization_gemini(self, step1_data: Dict[str, Any], llm_client) -> Dict[str, Any]:
        """Generate generalization using Gemini API with evidence-based strict schema."""
        analysis = step1_data.get("analysis", {})
        evidence_tracking = analysis.get("evidence_tracking", {})
        
        prompt = f"""You are a Technical Architect performing Logic Abstraction with EVIDENCE-BASED inference.

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
{json.dumps(analysis, indent=2)[:4000]}

Evidence Tracking:
{json.dumps(evidence_tracking, indent=2)[:1000]}

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

Respond ONLY with valid JSON, no additional text."""

        try:
            response = llm_client.client.models.generate_content(
                model=llm_client.model_name,
                contents=prompt
            )
            
            # Extract text from response
            if hasattr(response, 'text'):
                response_text = response.text.strip()
            elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                response_text = response.candidates[0].content.parts[0].text.strip()
            else:
                response_text = str(response)
            
            # Clean JSON response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            return json.loads(response_text)
        except Exception as e:
            raise Exception(f"Gemini generalization failed: {str(e)}")
    
    def _generate_llm_generalization_openai(self, step1_data: Dict[str, Any], llm_client) -> Dict[str, Any]:
        """Generate generalization using OpenAI API."""
        analysis = step1_data.get("analysis", {})
        
        prompt = f"""You are a Technical Architect specializing in abstracting software solutions.

Given the following product analysis, extract the Functional DNA by:
1. Stripping away product name and industry context
2. Identifying the abstract mathematical/structural problem
3. Mapping to cross-industry applications
4. Assessing integration complexity

Product Analysis:
{json.dumps(analysis, indent=2)[:6000]}

Provide a JSON response with this structure:
{{
    "functional_dna": {{
        "abstract_problem": "Abstract problem description without product/industry context",
        "core_algorithm": "Core algorithmic approach",
        "input_output_contract": {{
            "input_types": ["List of input types"],
            "output_types": ["List of output types"]
        }},
        "state_management": "How state is managed",
        "scalability_pattern": "Scalability approach"
    }},
    "market_reach": {{
        "primary_industry": "Current industry",
        "cross_industry_applications": ["List of other industries where this applies"],
        "utility_score": 1-10,
        "market_potential": "High/Medium/Low"
    }},
    "friction_report": {{
        "difficulty": "Low/Medium/High",
        "estimated_hours": int,
        "required_technologies": ["List"],
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
    }}
}}

Respond ONLY with valid JSON, no additional text."""

        try:
            response = llm_client.client.chat.completions.create(
                model=llm_client.model_name,
                messages=[
                    {"role": "system", "content": "You are a Technical Architect. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content.strip()
            return json.loads(response_text)
        except Exception as e:
            raise Exception(f"OpenAI generalization failed: {str(e)}")
    
    def _generate_llm_generalization_claude(self, step1_data: Dict[str, Any], llm_client) -> Dict[str, Any]:
        """Generate generalization using Claude API with evidence-based strict schema."""
        analysis = step1_data.get("analysis", {})
        evidence_tracking = analysis.get("evidence_tracking", {})

        prompt = f"""You are a Technical Architect performing Logic Abstraction with EVIDENCE-BASED inference.

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
{json.dumps(analysis, indent=2)[:6000]}

Evidence Tracking:
{json.dumps(evidence_tracking, indent=2)[:1000]}

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

Respond ONLY with valid JSON, no additional text."""

        try:
            return llm_client.generate_json(
                prompt,
                system="You are a Technical Architect. Respond only with valid JSON.",
                max_tokens=4096,
            )
        except Exception as e:
            raise Exception(f"Claude generalization failed: {str(e)}")

    def save_output(self, result: Dict[str, Any], output_file: Optional[str] = None,
                   format: str = "markdown") -> str:
        """Save generalization results to a file."""
        if output_file is None:
            # Generate filename from Step 1 URL
            step1_url = result.get("step1_data", {}).get("url", "unknown")
            domain = step1_url.replace("https://", "").replace("http://", "").split("/")[0]
            domain = domain.replace(".", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = "md" if format == "markdown" else "json"
            output_file = f"outputs/step2_{domain}_{timestamp}.{extension}"
        
        import os
        os.makedirs(os.path.dirname(output_file) if "/" in output_file else "outputs", exist_ok=True)
        
        if format == "markdown":
            markdown_content = self._generate_markdown_report(result)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
        else:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def _generate_markdown_report(self, result: Dict[str, Any]) -> str:
        """Generate a markdown report from generalization results."""
        step1_data = result.get("step1_data", {})
        generalization = result.get("generalization", {})
        url = step1_data.get("url", "Unknown")
        
        functional_dna = generalization.get("functional_dna", {})
        market_reach = generalization.get("market_reach", {})
        friction_report = generalization.get("friction_report", {})
        interface_map = generalization.get("interface_map", {})
        
        markdown = f"""# Step 2: Generalization Report

**Original URL:** {url}  
**Generalized:** {result.get('timestamp', 'Unknown')}

---

## Functional DNA

**Logic Archetype:** {functional_dna.get('logic_archetype', 'Unknown')}  
*Evidence:* {functional_dna.get('logic_archetype_evidence', 'No evidence')}

**Core Algorithmic Class:** {functional_dna.get('core_algorithmic_class', 'Unknown')}  
*Evidence:* {functional_dna.get('core_algorithmic_evidence', 'No evidence')}

**Data Contract Strictness:** {functional_dna.get('data_contract_strictness', 'Unknown')}  
*Evidence:* {functional_dna.get('data_contract_evidence', 'No evidence')}

**Concurrency Requirements:** {functional_dna.get('concurrency_requirements', 'Unknown')}  
*Evidence:* {functional_dna.get('concurrency_evidence', 'No evidence')}

**Repurposing Confidence:** {functional_dna.get('repurposing_confidence', 'N/A')}/10  
*Reasoning:* {functional_dna.get('repurposing_reasoning', 'No reasoning provided')}

**Abstract Problem:** {functional_dna.get('abstract_problem', 'Unknown')}  
**Core Algorithm:** {functional_dna.get('core_algorithm', 'Unknown')}  
**Complexity:** {functional_dna.get('complexity', 'Unknown')}

### Input/Output Contract
{json.dumps(functional_dna.get('input_output_contract', {}), indent=2)}

### State Management
{functional_dna.get('state_management', 'Unknown')}

### Scalability Pattern
{functional_dna.get('scalability_pattern', 'Unknown')}

### Data Flow
{functional_dna.get('data_flow', 'Unknown')}

### Concurrency Model
{functional_dna.get('concurrency_model', 'Unknown')}

### Error Handling
{functional_dna.get('error_handling', 'Unknown')}

### Performance Characteristics
{json.dumps(functional_dna.get('performance_characteristics', {}), indent=2)}

### Dependencies
{json.dumps(functional_dna.get('dependencies', {}), indent=2)}

### Language-Agnostic Pattern
{functional_dna.get('language_agnostic_pattern', 'Unknown')}

### Mathematical Model
{functional_dna.get('mathematical_model', 'Not Applicable')}

---

## Market Reach

**Primary Industry:** {market_reach.get('primary_industry', 'Unknown')}  
**Utility Score:** {market_reach.get('utility_score', 'N/A')}/10  
**Market Potential:** {market_reach.get('market_potential', 'Unknown')}

### Cross-Industry Applications
"""
        
        for industry in market_reach.get("cross_industry_applications", []):
            markdown += f"- {industry}\n"
        
        markdown += f"""
---

## Integration Friction Report

**Difficulty:** {friction_report.get('difficulty', 'Unknown')}  
**Estimated Hours:** {friction_report.get('estimated_hours', 'N/A')}  
**Risk Level:** {friction_report.get('risk_level', 'Unknown')}

### Required Technologies
"""
        
        for tech in friction_report.get("required_technologies", []):
            markdown += f"- {tech}\n"
        
        markdown += "\n### Complexity Factors\n"
        for factor in friction_report.get("complexity_factors", []):
            markdown += f"- {factor}\n"
        
        markdown += f"""
---

## Interface Map

**Standardization Level:** {interface_map.get('standardization_level', 'Unknown')}

### Adapter Schema
{json.dumps(interface_map.get('adapter_schema', {}), indent=2)}

---

*Report generated by SynchroB Step 2*
"""
        
        return markdown
