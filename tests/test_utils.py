"""
Tests for src/utils.py
"""

import json
import logging
import pytest
from src.utils import parse_llm_json_response, setup_logger


class TestParseLLMJsonResponse:
    """Test parse_llm_json_response function."""

    def test_parse_clean_json(self):
        """Test parsing clean JSON without markdown formatting."""
        text = '{"key": "value", "number": 42}'
        result = parse_llm_json_response(text)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_with_json_fence(self):
        """Test parsing JSON wrapped in ```json ... ``` fence."""
        text = """```json
{"key": "value", "list": [1, 2, 3]}
```"""
        result = parse_llm_json_response(text)
        assert result == {"key": "value", "list": [1, 2, 3]}

    def test_parse_json_with_generic_fence(self):
        """Test parsing JSON wrapped in generic ``` ... ``` fence."""
        text = """```
{"nested": {"field": "data"}}
```"""
        result = parse_llm_json_response(text)
        assert result == {"nested": {"field": "data"}}

    def test_parse_json_with_whitespace(self):
        """Test parsing JSON with leading/trailing whitespace."""
        text = """
        {"key": "value"}
        """
        result = parse_llm_json_response(text)
        assert result == {"key": "value"}

    def test_parse_json_with_all_fencing(self):
        """Test parsing JSON with fencing and whitespace."""
        text = """
        ```json
        {"spaced": true}
        ```
        """
        result = parse_llm_json_response(text)
        assert result == {"spaced": True}

    def test_parse_invalid_json_raises_error(self):
        """Test that invalid JSON raises JSONDecodeError."""
        text = '{"invalid": json}'
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json_response(text)

    def test_parse_empty_string_raises_error(self):
        """Test that empty string raises JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json_response("")

    def test_parse_empty_fence_raises_error(self):
        """Test that empty fence with no content raises error."""
        text = "```json\n```"
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json_response(text)

    def test_parse_complex_nested_structure(self):
        """Test parsing complex nested JSON."""
        text = """{
    "level1": {
        "level2": {
            "array": [1, 2, 3],
            "bool": true,
            "null": null
        }
    }
}"""
        result = parse_llm_json_response(text)
        assert result["level1"]["level2"]["array"] == [1, 2, 3]
        assert result["level1"]["level2"]["bool"] is True
        assert result["level1"]["level2"]["null"] is None


class TestSetupLogger:
    """Test setup_logger function."""

    def test_logger_creation(self):
        """Test that setup_logger returns a Logger instance."""
        logger = setup_logger("test_logger_1")
        assert isinstance(logger, logging.Logger)

    def test_logger_name(self):
        """Test that logger has the correct name."""
        logger_name = "test_logger_name_123"
        logger = setup_logger(logger_name)
        assert logger.name == logger_name

    def test_logger_level(self):
        """Test that logger has the correct level."""
        logger = setup_logger("test_logger_level", level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_logger_default_level(self):
        """Test that logger has default INFO level."""
        logger = setup_logger("test_logger_default")
        assert logger.level == logging.INFO

    def test_logger_has_handler(self):
        """Test that logger has at least one handler."""
        logger = setup_logger("test_logger_handler")
        assert len(logger.handlers) > 0

    def test_logger_handler_has_formatter(self):
        """Test that logger handler has a formatter."""
        logger = setup_logger("test_logger_formatter")
        assert logger.handlers[0].formatter is not None

    def test_no_duplicate_handlers_on_repeated_calls(self):
        """Test that repeated calls don't add duplicate handlers."""
        logger_name = "test_logger_no_dup"

        # First call
        logger1 = setup_logger(logger_name, level=logging.INFO)
        handler_count_1 = len(logger1.handlers)

        # Second call (should not add handler)
        logger2 = setup_logger(logger_name, level=logging.INFO)
        handler_count_2 = len(logger2.handlers)

        # Should be the same logger instance
        assert logger1 is logger2
        # Should have same number of handlers
        assert handler_count_1 == handler_count_2

    def test_logger_format_contains_required_fields(self):
        """Test that logger format includes required fields."""
        logger = setup_logger("test_logger_format")
        formatter = logger.handlers[0].formatter
        # The format string should contain %(asctime)s, %(name)s, etc.
        assert "%(asctime)s" in formatter._fmt
        assert "%(name)s" in formatter._fmt
        assert "%(levelname)s" in formatter._fmt
        assert "%(message)s" in formatter._fmt
