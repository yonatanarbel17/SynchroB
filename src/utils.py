"""
Shared utilities for SynchroB.

Provides:
- JSON parsing for LLM responses (handles markdown code fences)
- Standardized logger factory
- Retry decorator for transient API errors
- Content truncation constants
"""

import json
import logging
from typing import Callable, TypeVar
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Model context limits (in characters, conservative estimates)
GEMINI_CONTENT_LIMIT = 8000
OPENAI_CONTENT_LIMIT = 12000
DEFAULT_CONTENT_LIMIT = 5000


def parse_llm_json_response(text: str) -> dict:
    """
    Parse JSON from LLM response, handling markdown code fences.

    Consolidates duplicate parsing logic across:
    - src/discovery/llm_knowledge.py _parse_json_response
    - src/step1/analysis_strategy.py GeminiAnalysisStrategy (inline JSON cleanup)
    - src/analysis/gemini_client.py (inline json.loads calls)

    Args:
        text: Raw LLM response text, potentially containing markdown code fences

    Returns:
        Parsed JSON as dict

    Raises:
        json.JSONDecodeError: If the text is not valid JSON after cleaning
    """
    cleaned = text.strip()

    # Strip markdown code fences
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()
    return json.loads(cleaned)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Create and configure a standardized logger.

    Sets up a StreamHandler with a consistent format:
    "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: logging.INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Only add handler if one doesn't exist (avoid duplicates)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


F = TypeVar('F', bound=Callable)


def retry_on_transient_error(func: F) -> F:
    """
    Decorator for retrying API calls on transient errors.

    Retries up to 3 times with exponential backoff (1s start, 10s max).
    Only retries on:
    - requests.exceptions.ConnectionError
    - requests.exceptions.Timeout
    - requests.exceptions.HTTPError (for 429/5xx status codes)

    Args:
        func: Function to decorate

    Returns:
        Decorated function with retry logic
    """
    # Custom retry condition for HTTPError (only 429 and 5xx)
    def should_retry_http_error(exception: Exception) -> bool:
        if isinstance(exception, requests.exceptions.HTTPError):
            if hasattr(exception, 'response') and exception.response is not None:
                status_code = exception.response.status_code
                # Retry on rate limit (429) and server errors (5xx)
                return status_code == 429 or status_code >= 500
            return False
        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )) | retry_if_exception_type(requests.exceptions.HTTPError),
        reraise=True
    )
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            # Only retry if it's a transient error (429 or 5xx)
            if should_retry_http_error(e):
                # Log the retry attempt
                logger = logging.getLogger(__name__)
                status = getattr(e.response, 'status_code', 'unknown')
                logger.warning(
                    f"Transient HTTP error {status} in {func.__name__}, retrying..."
                )
                raise
            # Re-raise immediately for other HTTP errors (4xx except 429)
            raise

    return wrapper  # type: ignore
