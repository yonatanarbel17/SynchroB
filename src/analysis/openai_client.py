"""
OpenAI client for inference and semantic analysis.
Optimized for high-quality logical signature extraction and analysis.
"""

from typing import Optional, Dict, Any, List
import json
from openai import OpenAI
from config import config


class OpenAIClient:
    """
    Client for OpenAI API (GPT-4).
    
    Optimized for:
    - Logical signature extraction
    - High-quality semantic analysis
    - Complex code understanding
    - Accurate inference tasks
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key. If None, uses config.OPENAI_API_KEY
            model: Model name. If None, uses config.OPENAI_MODEL
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model_name = model or config.OPENAI_MODEL
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set OPENAI_API_KEY in .env or pass it to OpenAIClient."
            )
        
        self.client = OpenAI(api_key=self.api_key)
    
    def analyze_product(self, content: str, url: str) -> Dict[str, Any]:
        """
        Analyze product content and extract comprehensive information.
        
        Args:
            content: Scraped content from product page
            url: URL of the product page
        
        Returns:
            Dictionary with analysis including functionality, pricing, tech stack, etc.
        """
        prompt = f"""Analyze the following product page content and extract comprehensive information.

URL: {url}

Content:
{content[:12000]}  # Limit to avoid token limits

Provide a JSON response with the following structure:
{{
    "summary": "A 2-3 sentence summary of what this product does",
    "capabilities": [
        "List of main capabilities/features",
        "Each capability as a separate string"
    ],
    "use_cases": [
        "List of primary use cases",
        "Who would use this product"
    ],
    "technical_stack": [
        "Technologies, frameworks, languages, or platforms mentioned",
        "Be specific about versions if mentioned"
    ],
    "integrations": [
        "List of integrations with other services/tools",
        "APIs, plugins, or third-party services mentioned"
    ],
    "api_endpoints": [
        "List of API endpoints mentioned",
        "Or API documentation links if found"
    ],
    "pricing": {{
        "model": "pricing model (e.g., 'freemium', 'subscription', 'one-time', 'usage-based', 'enterprise', 'free', 'unknown')",
        "tiers": [
            "List of pricing tiers if mentioned",
            "Include price ranges if available"
        ],
        "free_tier": "Whether a free tier exists (true/false/unknown)",
        "notes": "Any pricing notes or details"
    }},
    "target_audience": "Who is this product for?",
    "category": "Product category (e.g., 'API', 'Database', 'Analytics', 'Authentication', 'Payment', 'Infrastructure', etc.)",
    "deployment": "Deployment options (e.g., 'cloud', 'on-premise', 'hybrid', 'SaaS', 'self-hosted', 'unknown')"
}}

Respond ONLY with valid JSON, no additional text or markdown formatting."""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing software products and extracting technical information. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent, factual output
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            analysis = json.loads(response_text)
            return analysis
            
        except json.JSONDecodeError as e:
            # Fallback: return structured error
            return {
                "summary": "Unable to parse LLM response",
                "capabilities": [],
                "use_cases": [],
                "technical_stack": [],
                "integrations": [],
                "api_endpoints": [],
                "pricing": {"model": "unknown", "tiers": [], "free_tier": "unknown", "notes": ""},
                "target_audience": "Unknown",
                "category": "Unknown",
                "deployment": "unknown",
                "error": str(e),
                "raw_response": response_text[:500] if 'response_text' in locals() else ""
            }
        except Exception as e:
            return {
                "summary": f"Error generating analysis: {str(e)}",
                "capabilities": [],
                "use_cases": [],
                "technical_stack": [],
                "integrations": [],
                "api_endpoints": [],
                "pricing": {"model": "unknown", "tiers": [], "free_tier": "unknown", "notes": ""},
                "target_audience": "Unknown",
                "category": "Unknown",
                "deployment": "unknown",
                "error": str(e)
            }
