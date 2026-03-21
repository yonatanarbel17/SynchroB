"""
Tests for src/cache.py
"""

import time
import json
import pytest
from pathlib import Path
from src.cache import ResultCache


class TestResultCache:
    """Test ResultCache class."""

    def test_cache_set_and_get(self, tmp_path):
        """Test setting and getting a value from cache."""
        cache = ResultCache(cache_dir=str(tmp_path), ttl=86400)

        test_data = {"field1": "value1", "field2": 42}
        cache.set("test_product", test_data, source="default")

        result = cache.get("test_product", source="default")
        assert result == test_data

    def test_cache_miss_returns_none(self, tmp_path):
        """Test that cache.get returns None for missing key."""
        cache = ResultCache(cache_dir=str(tmp_path), ttl=86400)

        result = cache.get("nonexistent_product", source="default")
        assert result is None

    def test_cache_expiry(self, tmp_path):
        """Test that cache expires after TTL."""
        cache = ResultCache(cache_dir=str(tmp_path), ttl=0.1)

        test_data = {"expiring": "data"}
        cache.set("expiring_product", test_data, source="default")

        # Should be available immediately
        result = cache.get("expiring_product", source="default")
        assert result == test_data

        # Wait for TTL to expire
        time.sleep(0.2)

        # Should now return None
        result = cache.get("expiring_product", source="default")
        assert result is None

    def test_cache_clear_removes_all_entries(self, tmp_path):
        """Test that clear() removes all cache entries."""
        cache = ResultCache(cache_dir=str(tmp_path), ttl=86400)

        # Add multiple entries
        cache.set("product1", {"data": 1}, source="default")
        cache.set("product2", {"data": 2}, source="github")
        cache.set("product3", {"data": 3}, source="openapi")

        # Verify they exist
        assert cache.get("product1", source="default") is not None
        assert cache.get("product2", source="github") is not None
        assert cache.get("product3", source="openapi") is not None

        # Clear cache
        count = cache.clear()

        # Should have removed 3 entries
        assert count == 3

        # Verify they're gone
        assert cache.get("product1", source="default") is None
        assert cache.get("product2", source="github") is None
        assert cache.get("product3", source="openapi") is None

    def test_make_key_consistency(self, tmp_path):
        """Test that _make_key produces consistent keys."""
        cache = ResultCache(cache_dir=str(tmp_path))

        key1 = cache._make_key("TestProduct", "github")
        key2 = cache._make_key("testproduct", "github")

        # Should be the same (case-insensitive, normalized)
        assert key1 == key2

    def test_make_key_different_for_different_sources(self, tmp_path):
        """Test that _make_key differs for different sources."""
        cache = ResultCache(cache_dir=str(tmp_path))

        key1 = cache._make_key("product", "source1")
        key2 = cache._make_key("product", "source2")

        # Should be different
        assert key1 != key2

    def test_cache_dir_created_on_init(self, tmp_path):
        """Test that cache directory is created on initialization."""
        cache_path = tmp_path / "new_cache_dir"
        assert not cache_path.exists()

        cache = ResultCache(cache_dir=str(cache_path))

        assert cache_path.exists()

    def test_cache_stores_cached_at_metadata(self, tmp_path):
        """Test that cache stores _cached_at timestamp."""
        cache = ResultCache(cache_dir=str(tmp_path), ttl=86400)

        cache.set("product", {"data": "value"}, source="default")

        key = cache._make_key("product", "default")
        cache_file = cache._cache_path(key)

        # Read raw file to check metadata
        content = json.loads(cache_file.read_text(encoding="utf-8"))
        assert "_cached_at" in content
        assert "_product_name" in content
        assert "_source" in content
        assert "result" in content
        assert content["result"] == {"data": "value"}

    def test_cache_handles_serialization_error_gracefully(self, tmp_path):
        """Test that cache.set handles non-serializable data gracefully."""
        cache = ResultCache(cache_dir=str(tmp_path))

        # Pass a datetime object which has a default serialization
        import datetime
        data = {"timestamp": datetime.datetime.now(), "value": 42}

        # Should not raise, should use default=str
        cache.set("datetime_product", data, source="default")

        # Should be retrievable
        result = cache.get("datetime_product", source="default")
        assert result is not None
        assert result["value"] == 42

    def test_cache_different_sources_independent(self, tmp_path):
        """Test that cache entries with different sources are independent."""
        cache = ResultCache(cache_dir=str(tmp_path))

        data1 = {"source": "github"}
        data2 = {"source": "openapi"}

        cache.set("product", data1, source="github")
        cache.set("product", data2, source="openapi")

        result1 = cache.get("product", source="github")
        result2 = cache.get("product", source="openapi")

        assert result1["source"] == "github"
        assert result2["source"] == "openapi"
