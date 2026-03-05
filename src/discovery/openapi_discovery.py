"""
OpenAPI/Swagger specification discovery source.

Probes well-known paths on a base URL to find and parse OpenAPI or Swagger
specification files. This is the highest-confidence source for API endpoint
information because specs are the canonical definition of an API.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import requests

from src.discovery.models import (
    SourceType,
    ConfidenceLevel,
    SourcedFact,
    SourcedEndpoint,
    SourceResult,
)

logger = logging.getLogger(__name__)

PROBE_PATHS = [
    "/openapi.json",
    "/openapi.yaml",
    "/swagger.json",
    "/swagger.yaml",
    "/api/openapi.json",
    "/api/swagger.json",
    "/api/v1/openapi.json",
    "/api/v1/swagger.json",
    "/api/v2/openapi.json",
    "/v1/openapi.json",
    "/v2/openapi.json",
    "/v3/openapi.json",
    "/.well-known/openapi",
    "/.well-known/openapi.json",
    "/api-docs",
    "/api-docs.json",
    "/docs/openapi.json",
    "/docs/swagger.json",
    "/swagger/v1/swagger.json",
]

REQUEST_TIMEOUT = 8


class OpenAPIDiscovery:
    """
    Discovers API information by probing for OpenAPI/Swagger specification
    files at well-known URL paths.

    When a valid spec is found it is parsed exhaustively to extract every
    endpoint, security scheme, and metadata field.
    """

    @staticmethod
    def _normalize_url(base_url: str) -> str:
        """Strip trailing slashes and ensure a scheme is present."""
        url = base_url.strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    @staticmethod
    def _is_valid_spec(data: dict) -> bool:
        """
        Return True if the parsed JSON looks like an OpenAPI or Swagger spec.
        """
        if not isinstance(data, dict):
            return False
        return any(key in data for key in ("openapi", "swagger", "paths"))

    def _probe_for_spec(self, base_url: str) -> Optional[Dict[str, Any]]:
        """
        Try each probe path against the base URL and return the first valid
        OpenAPI/Swagger spec found, along with the URL it was found at.

        Returns a tuple-like dict with keys "spec" and "spec_url", or None.
        """
        headers = {"Accept": "application/json"}

        for path in PROBE_PATHS:
            url = f"{base_url}{path}"
            try:
                resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    continue

                try:
                    data = json.loads(resp.text)
                except (json.JSONDecodeError, ValueError):
                    continue

                if self._is_valid_spec(data):
                    logger.info("Found valid spec at %s", url)
                    return {"spec": data, "spec_url": url}

            except requests.RequestException as exc:
                logger.debug("Probe failed for %s: %s", url, exc)
                continue

        return None

    def _extract_endpoints(
        self, spec: Dict[str, Any], spec_url: str
    ) -> List[SourcedEndpoint]:
        """
        Extract all API endpoints from the spec's paths object.
        """
        endpoints: List[SourcedEndpoint] = []
        paths = spec.get("paths", {})
        if not isinstance(paths, dict):
            return endpoints

        http_methods = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if method.lower() not in http_methods:
                    continue
                if not isinstance(operation, dict):
                    continue

                # Summary / description
                summary = operation.get("summary") or operation.get("description") or ""

                # Parameters (merge path-level and operation-level)
                params_raw = list(path_item.get("parameters", []))
                params_raw.extend(operation.get("parameters", []))
                parameters = []
                for param in params_raw:
                    if isinstance(param, dict):
                        parameters.append({
                            "name": param.get("name", ""),
                            "in": param.get("in", ""),
                            "required": param.get("required", False),
                            "description": param.get("description", ""),
                            "type": param.get("schema", {}).get("type", "")
                            if isinstance(param.get("schema"), dict)
                            else param.get("type", ""),
                        })

                # Response schema (look at 200 or 201 first, then default)
                response_schema = None
                responses = operation.get("responses", {})
                if isinstance(responses, dict):
                    for code in ("200", "201", "default"):
                        resp_obj = responses.get(code)
                        if not isinstance(resp_obj, dict):
                            continue
                        # OpenAPI 3.x: content -> application/json -> schema
                        content = resp_obj.get("content", {})
                        if isinstance(content, dict):
                            json_content = content.get("application/json", {})
                            if isinstance(json_content, dict) and "schema" in json_content:
                                response_schema = json_content["schema"]
                                break
                        # Swagger 2.x: schema directly on response
                        if "schema" in resp_obj:
                            response_schema = resp_obj["schema"]
                            break

                endpoints.append(SourcedEndpoint(
                    method=method.upper(),
                    path=path,
                    summary=summary if summary else None,
                    parameters=parameters if parameters else None,
                    response_schema=response_schema,
                    source=SourceType.OPENAPI_SPEC,
                    source_url=spec_url,
                    confidence=ConfidenceLevel.HIGH,
                ))

        return endpoints

    def _extract_security_schemes(
        self, spec: Dict[str, Any], spec_url: str
    ) -> List[SourcedFact]:
        """
        Extract authentication / security scheme information from the spec.
        Handles both Swagger 2.x (securityDefinitions) and OpenAPI 3.x
        (components.securitySchemes).
        """
        auth_methods: List[SourcedFact] = []
        seen: set = set()

        # Swagger 2.x
        security_defs = spec.get("securityDefinitions", {})
        if isinstance(security_defs, dict):
            for name, definition in security_defs.items():
                if not isinstance(definition, dict):
                    continue
                scheme_type = definition.get("type", "unknown")
                label = f"{name} ({scheme_type})"
                if label not in seen:
                    seen.add(label)
                    auth_methods.append(SourcedFact(
                        value=label,
                        source=SourceType.OPENAPI_SPEC,
                        source_url=spec_url,
                        confidence=ConfidenceLevel.HIGH,
                        raw_evidence=f"Swagger securityDefinition: {json.dumps(definition)[:300]}",
                    ))

        # OpenAPI 3.x
        components = spec.get("components", {})
        if isinstance(components, dict):
            security_schemes = components.get("securitySchemes", {})
            if isinstance(security_schemes, dict):
                for name, definition in security_schemes.items():
                    if not isinstance(definition, dict):
                        continue
                    scheme_type = definition.get("type", "unknown")
                    scheme_detail = definition.get("scheme", "")
                    label = f"{name} ({scheme_type}"
                    if scheme_detail:
                        label += f"/{scheme_detail}"
                    label += ")"
                    if label not in seen:
                        seen.add(label)
                        auth_methods.append(SourcedFact(
                            value=label,
                            source=SourceType.OPENAPI_SPEC,
                            source_url=spec_url,
                            confidence=ConfidenceLevel.HIGH,
                            raw_evidence=f"OpenAPI securityScheme: {json.dumps(definition)[:300]}",
                        ))

        return auth_methods

    def _extract_info(
        self, spec: Dict[str, Any], spec_url: str
    ) -> Dict[str, Any]:
        """
        Extract product info (title, description) from the spec's info object.
        """
        info = spec.get("info", {})
        result: Dict[str, Any] = {}
        if isinstance(info, dict):
            title = info.get("title", "")
            description = info.get("description", "")
            if title:
                result["product_name"] = title
            if description:
                result["description"] = description
            elif title:
                result["description"] = title
        return result

    def _extract_servers(self, spec: Dict[str, Any]) -> List[str]:
        """
        Extract server URLs from OpenAPI 3.x servers list or Swagger 2.x
        host/basePath.
        """
        urls: List[str] = []

        # OpenAPI 3.x
        servers = spec.get("servers", [])
        if isinstance(servers, list):
            for server in servers:
                if isinstance(server, dict) and server.get("url"):
                    urls.append(server["url"])

        # Swagger 2.x
        host = spec.get("host", "")
        if host:
            base_path = spec.get("basePath", "")
            schemes = spec.get("schemes", ["https"])
            scheme = schemes[0] if schemes else "https"
            urls.append(f"{scheme}://{host}{base_path}")

        return urls

    def discover(self, base_url: str) -> SourceResult:
        """
        Discover API information by probing for OpenAPI/Swagger specs.

        Args:
            base_url: The base URL to probe (e.g. "https://api.stripe.com").

        Returns:
            SourceResult with endpoints, auth methods, and the raw spec.
        """
        logger.info("OpenAPIDiscovery: probing %s for specs", base_url)

        normalized_url = self._normalize_url(base_url)
        probe_result = self._probe_for_spec(normalized_url)

        if probe_result is None:
            logger.info("No OpenAPI/Swagger spec found at %s", normalized_url)
            return SourceResult(
                source_type=SourceType.OPENAPI_SPEC,
                success=False,
                error=f"No OpenAPI/Swagger spec found at {normalized_url}",
                product_url=normalized_url,
            )

        spec = probe_result["spec"]
        spec_url = probe_result["spec_url"]

        # Extract all data from the spec
        info = self._extract_info(spec, spec_url)
        endpoints = self._extract_endpoints(spec, spec_url)
        auth_methods = self._extract_security_schemes(spec, spec_url)
        server_urls = self._extract_servers(spec)

        # Build capabilities from tag descriptions if present
        capabilities: List[SourcedFact] = []
        tags = spec.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, dict):
                    tag_name = tag.get("name", "")
                    tag_desc = tag.get("description", "")
                    label = tag_name
                    if tag_desc:
                        label = f"{tag_name}: {tag_desc}"
                    if label:
                        capabilities.append(SourcedFact(
                            value=label,
                            source=SourceType.OPENAPI_SPEC,
                            source_url=spec_url,
                            confidence=ConfidenceLevel.HIGH,
                            raw_evidence=f"OpenAPI tag: {tag_name}",
                        ))

        # Discovered URLs
        discovered_urls: Dict[str, str] = {"openapi_spec": spec_url}
        if server_urls:
            discovered_urls["api_server"] = server_urls[0]

        # Spec version as technical stack
        technical_stack: List[SourcedFact] = []
        spec_version = spec.get("openapi") or spec.get("swagger")
        if spec_version:
            spec_type = "OpenAPI" if "openapi" in spec else "Swagger"
            technical_stack.append(SourcedFact(
                value=f"{spec_type} {spec_version}",
                source=SourceType.OPENAPI_SPEC,
                source_url=spec_url,
                confidence=ConfidenceLevel.HIGH,
                raw_evidence=f"Spec version field: {spec_version}",
            ))

        logger.info(
            "Extracted %d endpoints, %d auth methods, %d capabilities from %s",
            len(endpoints), len(auth_methods), len(capabilities), spec_url,
        )

        return SourceResult(
            source_type=SourceType.OPENAPI_SPEC,
            success=True,
            product_name=info.get("product_name"),
            product_url=normalized_url,
            description=info.get("description"),
            capabilities=capabilities,
            api_endpoints=endpoints,
            openapi_spec=spec,
            auth_methods=auth_methods,
            technical_stack=technical_stack,
            discovered_urls=discovered_urls,
        )
