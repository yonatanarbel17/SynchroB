"""
Claude (Anthropic) client for inference and semantic analysis.
The go-to / default LLM for SynchroB — high-quality analysis with excellent
instruction-following for structured JSON output.
"""

import json
import os
import ssl
from typing import Optional, Dict, Any, List

import anthropic
import httpx
from src.utils import parse_llm_json_response
from config import config


class ClaudeClient:
    """
    Client for Anthropic Claude API.

    Default LLM for SynchroB — preferred for:
    - Product analysis (Step 1)
    - Generalization / Functional DNA extraction (Step 2)
    - Local repo analysis (repo-analyzer skill)
    - Domain classification
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key. If None, uses config.ANTHROPIC_API_KEY
            model: Model name. If None, uses config.CLAUDE_MODEL
        """
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        self.model_name = model or config.CLAUDE_MODEL

        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set ANTHROPIC_API_KEY in .env or pass it to ClaudeClient."
            )

        # If running behind a proxy with a self-signed cert, disable SSL verification
        # to avoid CERTIFICATE_VERIFY_FAILED errors. In production, remove this.
        http_client = None
        if os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"):
            http_client = httpx.Client(verify=False)

        self.client = anthropic.Anthropic(
            api_key=self.api_key,
            http_client=http_client,
        )

    def generate(self, prompt: str, system: Optional[str] = None, max_tokens: int = 4096) -> str:
        """
        Send a prompt to Claude and return the raw text response.

        Args:
            prompt: The user message / prompt
            system: Optional system message
            max_tokens: Maximum tokens in the response

        Returns:
            Raw text response from Claude
        """
        kwargs = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return response.content[0].text.strip()

    def generate_json(self, prompt: str, system: Optional[str] = None, max_tokens: int = 4096) -> Dict[str, Any]:
        """
        Send a prompt to Claude and parse the response as JSON.

        Args:
            prompt: The user message / prompt
            system: Optional system message
            max_tokens: Maximum tokens in the response

        Returns:
            Parsed JSON dict
        """
        text = self.generate(prompt, system=system, max_tokens=max_tokens)
        return parse_llm_json_response(text)

    def analyze_product(self, content: str, url: str) -> Dict[str, Any]:
        """
        Analyze product content and extract comprehensive information.
        Drop-in replacement for OpenAIClient.analyze_product().

        Args:
            content: Scraped content from product page
            url: URL of the product page

        Returns:
            Dictionary with analysis results
        """
        prompt = f"""Analyze the following product page content and extract comprehensive information.

URL: {url}

Content:
{content[:12000]}

Provide a JSON response with the following structure:
{{
    "summary": "A 2-3 sentence summary of what this product does",
    "capabilities": ["List of main capabilities/features"],
    "use_cases": ["List of primary use cases"],
    "technical_stack": ["Technologies, frameworks, languages mentioned"],
    "integrations": ["List of integrations with other services/tools"],
    "api_endpoints": ["List of API endpoints mentioned"],
    "pricing": {{
        "model": "pricing model",
        "tiers": ["List of pricing tiers"],
        "free_tier": "true/false/unknown",
        "notes": "Any pricing notes"
    }},
    "target_audience": "Who is this product for?",
    "category": "Product category",
    "deployment": "Deployment options"
}}

Respond ONLY with valid JSON, no additional text or markdown formatting."""

        system = (
            "You are an expert at analyzing software products and extracting "
            "technical information. Always respond with valid JSON only. "
            "Strip all marketing language. Focus on technical facts with evidence."
        )

        try:
            return self.generate_json(prompt, system=system)
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
                "error": str(e),
            }

    def classify_domain(self, signature: Dict[str, Any], context: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify a functional signature into problem domains.
        Drop-in replacement for GeminiClient.classify_domain().
        """
        prompt = f"""Analyze the following functional signature and classify it into problem domains.

Functional Signature:
{signature}

{context if context else ''}

Provide a JSON response with:
- problem_domain: Main problem domain
- subcategory: Specific subcategory
- use_cases: List of use cases
- compatibility_tags: List of compatibility tags

Respond in valid JSON format only."""

        try:
            return self.generate_json(prompt)
        except Exception as e:
            raise Exception(f"Error classifying domain: {str(e)}")

    def summarize_content(self, content: str, max_length: int = 200) -> str:
        """
        Summarize scraped content.
        Drop-in replacement for GeminiClient.summarize_content().
        """
        prompt = f"""Summarize the following technical content in {max_length} words or less, focusing on:
- Core functionality
- Key features
- Technical requirements

Content:
{content[:5000]}

Summary:"""

        try:
            return self.generate(prompt)
        except Exception as e:
            raise Exception(f"Error summarizing content: {str(e)}")
