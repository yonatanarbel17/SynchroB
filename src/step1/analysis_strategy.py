"""
Analysis Strategy Pattern: Abstract interface for different analysis methods.
This allows easy switching between direct analysis, LLM-based analysis, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class AnalysisStrategy(ABC):
    """Abstract base class for analysis strategies."""
    
    @abstractmethod
    def analyze(self, scraped_data: Dict[str, Any], extracted_data: Dict[str, Any], url: str) -> Dict[str, Any]:
        """
        Analyze product data and return structured analysis.
        
        Args:
            scraped_data: Raw scraped data (markdown, html, metadata)
            extracted_data: Pre-extracted structured data (title, headings, features, etc.)
            url: Original product URL
            
        Returns:
            Dictionary with analysis results (summary, capabilities, use_cases, etc.)
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this analysis strategy."""
        pass


class DirectAnalysisStrategy(AnalysisStrategy):
    """Direct intelligent analysis using pattern matching and heuristics (no LLM)."""
    
    def __init__(self, processor):
        """
        Initialize direct analysis strategy.
        
        Args:
            processor: Reference to Step1Processor for accessing helper methods
        """
        self.processor = processor
    
    def analyze(self, scraped_data: Dict[str, Any], extracted_data: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Generate analysis using intelligent pattern matching."""
        markdown = scraped_data.get("markdown", "")
        return self.processor._generate_intelligent_analysis(markdown, extracted_data, url)
    
    def get_name(self) -> str:
        return "Direct Intelligent Analysis"


class GeminiAnalysisStrategy(AnalysisStrategy):
    """Analysis using Google Gemini API."""
    
    def __init__(self, processor, gemini_client):
        """
        Initialize Gemini analysis strategy.
        
        Args:
            processor: Reference to Step1Processor for accessing helper methods
            gemini_client: Initialized GeminiClient instance
        """
        self.processor = processor
        self.llm = gemini_client
    
    def analyze(self, scraped_data: Dict[str, Any], extracted_data: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Generate analysis using Gemini API."""
        markdown = scraped_data.get("markdown", "")
        title = extracted_data.get("title", "Unknown Product")
        content_preview = markdown[:8000]
        headings = extracted_data.get("headings", [])
        code_blocks = extracted_data.get("code_blocks", [])
        
        prompt = f"""You are a Technical Documentation Extractor. Your goal is to extract ONLY technical facts, stripping all marketing language.

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

Respond ONLY with valid JSON, no additional text."""

        try:
            response = self.llm.client.models.generate_content(
                model=self.llm.model_name,
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
            import json
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            analysis = json.loads(response_text)
            return analysis
            
        except Exception as e:
            print(f"⚠️  Gemini analysis failed: {str(e)}")
            print("🔄 Falling back to direct intelligent analysis...")
            # Fallback to direct analysis
            return self.processor._generate_intelligent_analysis(markdown, extracted_data, url)
    
    def get_name(self) -> str:
        return "Gemini API Analysis"


class OpenAIAnalysisStrategy(AnalysisStrategy):
    """Analysis using OpenAI GPT API."""
    
    def __init__(self, processor, openai_client):
        """
        Initialize OpenAI analysis strategy.
        
        Args:
            processor: Reference to Step1Processor for accessing helper methods
            openai_client: Initialized OpenAIClient instance
        """
        self.processor = processor
        self.llm = openai_client
    
    def analyze(self, scraped_data: Dict[str, Any], extracted_data: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Generate analysis using OpenAI API."""
        markdown = scraped_data.get("markdown", "")
        content_preview = markdown[:12000]
        
        try:
            return self.llm.analyze_product(content_preview, url)
        except Exception as e:
            print(f"⚠️  OpenAI analysis failed: {str(e)}")
            print("🔄 Falling back to direct intelligent analysis...")
            # Fallback to direct analysis
            return self.processor._generate_intelligent_analysis(markdown, extracted_data, url)
    
    def get_name(self) -> str:
        return "OpenAI GPT Analysis"
