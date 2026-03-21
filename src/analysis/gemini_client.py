"""
Gemini client for inference and semantic analysis.
Optimized for cost-effective classification and domain mapping.
"""

from typing import Optional, Dict, Any, List
import google.genai as genai
from src.utils import parse_llm_json_response
from config import config


class GeminiClient:
    """
    Client for Google Gemini API.
    
    Optimized for:
    - Domain classification
    - Content summarization
    - High-volume inference tasks
    - Cost-effective processing
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Gemini API key. If None, uses config.GEMINI_API_KEY
            model: Model name. If None, uses config.GEMINI_MODEL
        """
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model_name = model or config.GEMINI_MODEL
        
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. "
                "Set GEMINI_API_KEY in .env or pass it to GeminiClient."
            )
        
        self.client = genai.Client(api_key=self.api_key)
    
    def classify_domain(self, signature: Dict[str, Any], context: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify a functional signature into problem domains.
        
        Args:
            signature: Functional fingerprint/logical signature
            context: Optional additional context
        
        Returns:
            Dictionary with domain classification
        """
        prompt = f"""Analyze the following functional signature and classify it into problem domains.

Functional Signature:
{signature}

{context if context else ''}

Provide a JSON response with:
- problem_domain: Main problem domain (e.g., "optimization", "data-processing", "authentication")
- subcategory: Specific subcategory
- use_cases: List of use cases
- compatibility_tags: List of compatibility tags

Respond in valid JSON format only."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            # Parse JSON from response (handles markdown code fences)
            result = parse_llm_json_response(response.text)
            return result
        except Exception as e:
            raise Exception(f"Error classifying domain: {str(e)}")
    
    def summarize_content(self, content: str, max_length: int = 200) -> str:
        """
        Summarize scraped content.
        
        Args:
            content: Content to summarize
            max_length: Maximum summary length
        
        Returns:
            Summarized content
        """
        prompt = f"""Summarize the following technical content in {max_length} words or less, focusing on:
- Core functionality
- Key features
- Technical requirements

Content:
{content[:5000]}  # Limit input to avoid token limits

Summary:"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            raise Exception(f"Error summarizing content: {str(e)}")
    
    def extract_key_concepts(self, content: str) -> List[str]:
        """
        Extract key technical concepts from content.
        
        Args:
            content: Content to analyze
        
        Returns:
            List of key concepts
        """
        prompt = f"""Extract the key technical concepts, technologies, and frameworks mentioned in the following content.
Return only a comma-separated list of concepts.

Content:
{content[:3000]}

Key concepts:"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            concepts = [c.strip() for c in response.text.strip().split(",")]
            return concepts
        except Exception as e:
            raise Exception(f"Error extracting concepts: {str(e)}")
    
    def infer_abstract_schema(self, logical_signature: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a unified abstract schema from logical signature.
        
        Args:
            logical_signature: Logical signature from code analysis
        
        Returns:
            Unified abstract schema
        """
        prompt = f"""Convert the following logical signature into a unified abstract schema.

Logical Signature:
{logical_signature}

Provide a JSON schema with:
- type: Type of component (e.g., "optimization_engine", "data_processor")
- inputs: Standardized input schema
- outputs: Standardized output schema
- constraints: List of constraints
- compatibility: Compatibility requirements

Respond in valid JSON format only."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            schema = parse_llm_json_response(response.text)
            return schema
        except Exception as e:
            raise Exception(f"Error inferring abstract schema: {str(e)}")
