"""
LLM knowledge base discovery source.

Queries an LLM (Gemini or OpenAI) for its pre-existing knowledge about a product.
This serves as the BASELINE — facts are LOW confidence until confirmed by other sources.
"""

import json
import logging
from typing import Optional

from src.discovery.models import (
    SourceType,
    ConfidenceLevel,
    SourcedFact,
    SourcedEndpoint,
    SourceResult,
)

logger = logging.getLogger(__name__)

PRODUCT_QUERY_PROMPT = """You are a Technical Product Analyst. Provide factual technical information about "{product_name}".
{url_context}

Respond ONLY with valid JSON containing:
{{
    "description": "2-3 sentence technical description of what the product does (NO marketing language, focus on data operations and architecture)",
    "capabilities": ["list of technical capabilities - what it actually does functionally, not marketing claims. Each should describe a data operation or technical function."],
    "api_type": "REST/GraphQL/gRPC/SOAP/WebSocket/None/Unknown",
    "known_endpoints": ["list of known API endpoint patterns, e.g. 'POST /v1/charges', 'GET /v1/customers/{{id}}'. Only include endpoints you are confident exist."],
    "sdk_languages": ["list of official SDK/client library languages available, e.g. 'Python', 'Node.js', 'Ruby'"],
    "authentication_methods": ["list of auth methods supported: 'API Key', 'OAuth 2.0', 'JWT', 'Basic Auth', etc."],
    "integrations": ["list of known integrations with other products/platforms"],
    "technical_stack": ["known technologies used in the product (programming languages, databases, infrastructure)"],
    "architecture_pattern": "event-driven/microservices/monolith/serverless/unknown",
    "deployment_model": "SaaS/on-premise/hybrid/SDK-only/unknown",
    "data_formats": ["supported data formats like JSON, XML, CSV, Protobuf"],
    "webhook_support": "yes/no/unknown",
    "rate_limiting": "description of known rate limits or 'unknown'",
    "github_repo": "URL of main GitHub repository if known, or null",
    "documentation_url": "URL of developer documentation if known, or null",
    "homepage_url": "URL of product homepage if known, or null",
    "pricing_model": "free/freemium/subscription/usage-based/enterprise/unknown"
}}

IMPORTANT:
- Only include information you are confident about.
- Use "unknown" or empty lists for things you're unsure of.
- Do NOT make up API endpoints or capabilities.
- Focus on TECHNICAL facts, not marketing descriptions.
- For capabilities, describe data operations: what it reads, writes, transforms, matches, routes."""


class LLMKnowledgeDiscovery:
    """Query LLM knowledge base for product information."""

    def __init__(self, gemini_client=None, openai_client=None):
        """
        Initialize with existing LLM client instances.

        Args:
            gemini_client: Initialized GeminiClient (preferred, cheaper)
            openai_client: Initialized OpenAIClient (fallback)
        """
        self.gemini_client = gemini_client
        self.openai_client = openai_client

    def discover(self, product_name: str, product_url: Optional[str] = None) -> SourceResult:
        """
        Ask the LLM what it knows about this product.

        The LLM result serves as the BASELINE. All facts get LOW confidence
        because they are not from an authoritative source. Other sources
        (OpenAPI, GitHub, package registries) confirm or refute these facts,
        upgrading confidence when multiple sources agree.
        """
        logger.info("Querying LLM knowledge base for '%s'", product_name)

        url_context = f'Their website is: {product_url}' if product_url else ''
        prompt = PRODUCT_QUERY_PROMPT.format(
            product_name=product_name,
            url_context=url_context,
        )

        response_text = None

        # Try Gemini first (cheaper)
        if self.gemini_client:
            response_text = self._query_gemini(prompt)

        # Fall back to OpenAI
        if response_text is None and self.openai_client:
            response_text = self._query_openai(prompt)

        if response_text is None:
            logger.warning("No LLM client available or all queries failed")
            return SourceResult(
                source_type=SourceType.LLM_KNOWLEDGE,
                success=False,
                error="No LLM client available or all queries failed",
            )

        # Parse JSON response
        try:
            data = self._parse_json_response(response_text)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse LLM response as JSON: %s", exc)
            return SourceResult(
                source_type=SourceType.LLM_KNOWLEDGE,
                success=False,
                error=f"JSON parse error: {exc}",
            )

        return self._build_source_result(data, product_name, product_url)

    # ------------------------------------------------------------------
    # LLM query helpers
    # ------------------------------------------------------------------

    def _query_gemini(self, prompt: str) -> Optional[str]:
        """Query Gemini API and return raw text response."""
        try:
            response = self.gemini_client.client.models.generate_content(
                model=self.gemini_client.model_name,
                contents=prompt,
            )
            if hasattr(response, 'text'):
                return response.text.strip()
            if hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text.strip()
            return str(response)
        except Exception as exc:
            logger.warning("Gemini query failed: %s", exc)
            return None

    def _query_openai(self, prompt: str) -> Optional[str]:
        """Query OpenAI API and return raw text response."""
        try:
            response = self.openai_client.client.chat.completions.create(
                model=self.openai_client.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Technical Product Analyst. "
                            "Respond only with valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.warning("OpenAI query failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """Parse JSON from LLM response, handling markdown code fences."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        return json.loads(cleaned)

    def _build_source_result(
        self,
        data: dict,
        product_name: str,
        product_url: Optional[str],
    ) -> SourceResult:
        """Convert parsed LLM JSON into a SourceResult."""

        result = SourceResult(
            source_type=SourceType.LLM_KNOWLEDGE,
            success=True,
            product_name=product_name,
            product_url=product_url,
            description=data.get("description"),
        )

        src = SourceType.LLM_KNOWLEDGE
        conf = ConfidenceLevel.LOW  # All LLM facts are low confidence

        # Capabilities
        for cap in data.get("capabilities", []):
            if cap and isinstance(cap, str) and len(cap.strip()) > 3:
                result.capabilities.append(
                    SourcedFact(value=cap.strip(), source=src, confidence=conf)
                )

        # API endpoints
        for ep_str in data.get("known_endpoints", []):
            if not ep_str or not isinstance(ep_str, str):
                continue
            parts = ep_str.strip().split(" ", 1)
            if len(parts) == 2:
                method, path = parts[0].upper(), parts[1]
            else:
                method, path = None, parts[0]
            result.api_endpoints.append(
                SourcedEndpoint(
                    method=method, path=path, source=src, confidence=conf
                )
            )

        # Auth methods
        for auth in data.get("authentication_methods", []):
            if auth and isinstance(auth, str):
                result.auth_methods.append(
                    SourcedFact(value=auth.strip(), source=src, confidence=conf)
                )

        # SDK languages
        for lang in data.get("sdk_languages", []):
            if lang and isinstance(lang, str):
                result.sdk_languages.append(
                    SourcedFact(value=lang.strip(), source=src, confidence=conf)
                )

        # Dependencies / integrations
        for integ in data.get("integrations", []):
            if integ and isinstance(integ, str):
                result.integrations.append(
                    SourcedFact(value=integ.strip(), source=src, confidence=conf)
                )

        # Technical stack
        for tech in data.get("technical_stack", []):
            if tech and isinstance(tech, str):
                result.technical_stack.append(
                    SourcedFact(value=tech.strip(), source=src, confidence=conf)
                )

        # Architecture patterns
        arch = data.get("architecture_pattern", "")
        if arch and arch != "unknown":
            result.architecture_patterns.append(
                SourcedFact(value=arch.strip(), source=src, confidence=conf)
            )

        # Deployment options
        deploy = data.get("deployment_model", "")
        if deploy and deploy != "unknown":
            result.deployment_options.append(
                SourcedFact(value=deploy.strip(), source=src, confidence=conf)
            )

        # Data formats → capabilities
        for fmt in data.get("data_formats", []):
            if fmt and isinstance(fmt, str):
                result.capabilities.append(
                    SourcedFact(
                        value=f"Supports {fmt} data format",
                        source=src,
                        confidence=conf,
                    )
                )

        # Webhook support
        webhook = data.get("webhook_support", "unknown")
        if webhook and webhook.lower() in ("yes", "true"):
            result.capabilities.append(
                SourcedFact(
                    value="Webhook support for event notifications",
                    source=src,
                    confidence=conf,
                )
            )

        # Rate limiting info
        rate = data.get("rate_limiting", "unknown")
        if rate and rate.lower() != "unknown":
            result.capabilities.append(
                SourcedFact(
                    value=f"Rate limiting: {rate}",
                    source=src,
                    confidence=conf,
                )
            )

        # Discovered URLs
        github_url = data.get("github_repo")
        if github_url and isinstance(github_url, str) and "github.com" in github_url:
            result.discovered_urls["github_repo"] = github_url

        docs_url = data.get("documentation_url")
        if docs_url and isinstance(docs_url, str) and docs_url.startswith("http"):
            result.discovered_urls["docs"] = docs_url

        homepage = data.get("homepage_url")
        if homepage and isinstance(homepage, str) and homepage.startswith("http"):
            result.discovered_urls["product_url"] = homepage

        # Build raw content summary for downstream analysis
        summary_parts = []
        if data.get("description"):
            summary_parts.append(f"# {product_name}\n\n{data['description']}")
        if data.get("capabilities"):
            summary_parts.append(
                "## Capabilities\n"
                + "\n".join(f"- {c}" for c in data["capabilities"])
            )
        api_type = data.get("api_type", "Unknown")
        if api_type and api_type != "Unknown":
            summary_parts.append(f"## API\nAPI Type: {api_type}")
        if data.get("known_endpoints"):
            summary_parts.append(
                "## Endpoints\n"
                + "\n".join(f"- `{e}`" for e in data["known_endpoints"])
            )
        if summary_parts:
            result.raw_content = "\n\n".join(summary_parts)

        logger.info(
            "LLM knowledge: %d capabilities, %d endpoints, %d SDKs",
            len(result.capabilities),
            len(result.api_endpoints),
            len(result.sdk_languages),
        )

        return result
