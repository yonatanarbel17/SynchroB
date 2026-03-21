"""
Simple file-based cache for discovery and analysis results.

Caches results keyed by product name + source type, with configurable TTL.
"""

import hashlib
import json
import os
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache")
DEFAULT_TTL_SECONDS = 86400  # 24 hours


class ResultCache:
    """File-based cache for discovery and analysis results."""

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR, ttl: int = DEFAULT_TTL_SECONDS):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, product_name: str, source: str = "default") -> str:
        """Generate a filesystem-safe cache key."""
        raw = f"{product_name.lower().strip()}:{source}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, product_name: str, source: str = "default") -> Optional[Dict[str, Any]]:
        """Retrieve a cached result, or None if expired/missing."""
        key = self._make_key(product_name, source)
        path = self._cache_path(key)

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cached_at = data.get("_cached_at", 0)
            if time.time() - cached_at > self.ttl:
                logger.debug("Cache expired for %s:%s", product_name, source)
                path.unlink(missing_ok=True)
                return None
            logger.info("Cache hit for %s:%s", product_name, source)
            return data.get("result")
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("Cache read error: %s", e)
            return None

    def set(self, product_name: str, result: Dict[str, Any], source: str = "default") -> None:
        """Store a result in the cache."""
        key = self._make_key(product_name, source)
        path = self._cache_path(key)

        data = {
            "_cached_at": time.time(),
            "_product_name": product_name,
            "_source": source,
            "result": result,
        }

        try:
            path.write_text(json.dumps(data, default=str), encoding="utf-8")
            logger.debug("Cached result for %s:%s", product_name, source)
        except OSError as e:
            logger.warning("Cache write error: %s", e)

    def clear(self) -> int:
        """Clear all cached results. Returns count of files removed."""
        count = 0
        for path in self.cache_dir.glob("*.json"):
            try:
                path.unlink()
                count += 1
            except OSError:
                pass
        return count
