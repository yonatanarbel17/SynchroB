"""
Tests for src/step1/analysis_strategy.py and src/step2/generalization_strategy.py
"""

import pytest
from unittest.mock import MagicMock, patch
from src.step1.analysis_strategy import (
    DirectAnalysisStrategy,
    GeminiAnalysisStrategy,
    OpenAIAnalysisStrategy,
    ClaudeAnalysisStrategy,
)
from src.step2.generalization_strategy import (
    DirectGeneralizationStrategy,
    GeminiGeneralizationStrategy,
    OpenAIGeneralizationStrategy,
    ClaudeGeneralizationStrategy,
)


class TestDirectAnalysisStrategy:
    """Test DirectAnalysisStrategy."""

    def test_direct_analysis_calls_provided_callable(self):
        """Test that analyze() calls the provided callable."""
        mock_analyze_fn = MagicMock(return_value={"summary": "test result"})

        strategy = DirectAnalysisStrategy(mock_analyze_fn)

        scraped_data = {"markdown": "# Test\nSome content"}
        extracted_data = {"title": "Test Product", "headings": ["Test"]}
        url = "https://example.com"

        result = strategy.analyze(scraped_data, extracted_data, url)

        # Verify the callable was called
        mock_analyze_fn.assert_called_once()
        # First argument should be markdown
        assert mock_analyze_fn.call_args[0][0] == "# Test\nSome content"
        # Result should be what the callable returned
        assert result == {"summary": "test result"}

    def test_direct_analysis_get_name(self):
        """Test that get_name() returns correct name."""
        mock_analyze_fn = MagicMock()
        strategy = DirectAnalysisStrategy(mock_analyze_fn)

        assert strategy.get_name() == "Direct Intelligent Analysis"

    def test_direct_analysis_extracts_markdown_from_scraped_data(self):
        """Test that markdown is extracted from scraped_data."""
        mock_analyze_fn = MagicMock(return_value={})

        strategy = DirectAnalysisStrategy(mock_analyze_fn)

        scraped_data = {
            "markdown": "# Heading\n\nContent",
            "html": "<html>...</html>",
        }
        extracted_data = {}

        strategy.analyze(scraped_data, extracted_data, "http://test.com")

        # First argument should be the markdown
        call_args = mock_analyze_fn.call_args[0]
        assert call_args[0] == "# Heading\n\nContent"


class TestGeminiAnalysisStrategy:
    """Test GeminiAnalysisStrategy with mocked Gemini client."""

    @patch('src.step1.analysis_strategy.parse_llm_json_response')
    def test_gemini_analysis_calls_llm(self, mock_parse):
        """Test that analyze() calls Gemini API."""
        mock_parse.return_value = {"summary": "gemini result"}

        mock_gemini_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"summary": "gemini result"}'
        mock_gemini_client.client.models.generate_content.return_value = mock_response
        mock_gemini_client.model_name = "gemini-1.5-pro"

        mock_fallback_fn = MagicMock()

        strategy = GeminiAnalysisStrategy(mock_fallback_fn, mock_gemini_client)

        scraped_data = {"markdown": "# Test\nContent"}
        extracted_data = {"title": "Test Product"}
        url = "https://example.com"

        result = strategy.analyze(scraped_data, extracted_data, url)

        # Should call Gemini, not fallback
        mock_gemini_client.client.models.generate_content.assert_called_once()
        mock_fallback_fn.assert_not_called()
        assert result == {"summary": "gemini result"}

    def test_gemini_analysis_fallback_on_error(self):
        """Test that Gemini strategy falls back on error."""
        mock_fallback_fn = MagicMock(return_value={"summary": "fallback result"})

        mock_gemini_client = MagicMock()
        mock_gemini_client.client.models.generate_content.side_effect = Exception(
            "API Error"
        )

        strategy = GeminiAnalysisStrategy(mock_fallback_fn, mock_gemini_client)

        scraped_data = {"markdown": "# Test"}
        extracted_data = {"title": "Test"}

        result = strategy.analyze(scraped_data, extracted_data, "http://test.com")

        # Should fall back to direct analysis
        mock_fallback_fn.assert_called_once()
        assert result == {"summary": "fallback result"}

    def test_gemini_analysis_get_name(self):
        """Test that get_name() returns correct name."""
        strategy = GeminiAnalysisStrategy(
            MagicMock(), MagicMock()
        )
        assert strategy.get_name() == "Gemini API Analysis"

    def test_gemini_analysis_extracts_text_from_response(self):
        """Test extraction of text from various Gemini response formats."""
        mock_parse = MagicMock(return_value={})
        mock_gemini_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "json response"
        mock_gemini_client.client.models.generate_content.return_value = mock_response
        mock_gemini_client.model_name = "test"

        with patch('src.step1.analysis_strategy.parse_llm_json_response', mock_parse):
            strategy = GeminiAnalysisStrategy(MagicMock(), mock_gemini_client)
            strategy.analyze({"markdown": "test"}, {"title": "test"}, "http://test")

            # Should have called parse with the response text
            mock_parse.assert_called_once()


class TestOpenAIAnalysisStrategy:
    """Test OpenAIAnalysisStrategy with mocked OpenAI client."""

    def test_openai_analysis_calls_llm(self):
        """Test that analyze() calls OpenAI API."""
        mock_openai_client = MagicMock()
        mock_openai_client.analyze_product.return_value = {"summary": "openai result"}

        mock_fallback_fn = MagicMock()

        strategy = OpenAIAnalysisStrategy(mock_fallback_fn, mock_openai_client)

        scraped_data = {"markdown": "# Test\nContent"}
        extracted_data = {"title": "Test Product"}
        url = "https://example.com"

        result = strategy.analyze(scraped_data, extracted_data, url)

        # Should call OpenAI
        mock_openai_client.analyze_product.assert_called_once()
        mock_fallback_fn.assert_not_called()
        assert result == {"summary": "openai result"}

    def test_openai_analysis_fallback_on_error(self):
        """Test that OpenAI strategy falls back on error."""
        mock_fallback_fn = MagicMock(return_value={"summary": "fallback result"})

        mock_openai_client = MagicMock()
        mock_openai_client.analyze_product.side_effect = Exception("API Error")

        strategy = OpenAIAnalysisStrategy(mock_fallback_fn, mock_openai_client)

        scraped_data = {"markdown": "# Test"}
        extracted_data = {"title": "Test"}

        result = strategy.analyze(scraped_data, extracted_data, "http://test.com")

        # Should fall back to direct analysis
        mock_fallback_fn.assert_called_once()
        assert result == {"summary": "fallback result"}

    def test_openai_analysis_get_name(self):
        """Test that get_name() returns correct name."""
        strategy = OpenAIAnalysisStrategy(
            MagicMock(), MagicMock()
        )
        assert strategy.get_name() == "OpenAI GPT Analysis"


class TestDirectGeneralizationStrategy:
    """Test DirectGeneralizationStrategy."""

    def test_direct_generalization_calls_provided_callable(self):
        """Test that generalize() calls the provided callable."""
        mock_generalize_fn = MagicMock(return_value={"functional_dna": "test"})

        strategy = DirectGeneralizationStrategy(mock_generalize_fn)

        step1_data = {
            "analysis": {"summary": "test"},
            "url": "https://example.com",
        }

        result = strategy.generalize(step1_data)

        # Verify the callable was called
        mock_generalize_fn.assert_called_once_with(step1_data)
        assert result == {"functional_dna": "test"}

    def test_direct_generalization_get_name(self):
        """Test that get_name() returns correct name."""
        strategy = DirectGeneralizationStrategy(MagicMock())
        assert strategy.get_name() == "Direct Intelligent Generalization"


class TestGeminiGeneralizationStrategy:
    """Test GeminiGeneralizationStrategy."""

    def test_gemini_generalization_calls_llm_fn(self):
        """Test that generalize() calls the LLM function."""
        mock_llm_fn = MagicMock(return_value={"functional_dna": "gemini result"})
        mock_fallback_fn = MagicMock()
        mock_gemini_client = MagicMock()

        strategy = GeminiGeneralizationStrategy(
            mock_fallback_fn, mock_llm_fn, mock_gemini_client
        )

        step1_data = {"analysis": {"summary": "test"}}

        result = strategy.generalize(step1_data)

        # Should call LLM function with step1_data and client
        mock_llm_fn.assert_called_once_with(step1_data, mock_gemini_client)
        mock_fallback_fn.assert_not_called()
        assert result == {"functional_dna": "gemini result"}

    def test_gemini_generalization_fallback_on_error(self):
        """Test that Gemini generalization falls back on error."""
        mock_llm_fn = MagicMock(side_effect=Exception("LLM Error"))
        mock_fallback_fn = MagicMock(return_value={"functional_dna": "fallback"})
        mock_gemini_client = MagicMock()

        strategy = GeminiGeneralizationStrategy(
            mock_fallback_fn, mock_llm_fn, mock_gemini_client
        )

        step1_data = {"analysis": {"summary": "test"}}

        result = strategy.generalize(step1_data)

        # Should fall back to direct generalization
        mock_llm_fn.assert_called_once()
        mock_fallback_fn.assert_called_once_with(step1_data)
        assert result == {"functional_dna": "fallback"}

    def test_gemini_generalization_get_name(self):
        """Test that get_name() returns correct name."""
        strategy = GeminiGeneralizationStrategy(
            MagicMock(), MagicMock(), MagicMock()
        )
        assert strategy.get_name() == "Gemini API Generalization"


class TestOpenAIGeneralizationStrategy:
    """Test OpenAIGeneralizationStrategy."""

    def test_openai_generalization_calls_llm_fn(self):
        """Test that generalize() calls the LLM function."""
        mock_llm_fn = MagicMock(return_value={"functional_dna": "openai result"})
        mock_fallback_fn = MagicMock()
        mock_openai_client = MagicMock()

        strategy = OpenAIGeneralizationStrategy(
            mock_fallback_fn, mock_llm_fn, mock_openai_client
        )

        step1_data = {"analysis": {"summary": "test"}}

        result = strategy.generalize(step1_data)

        # Should call LLM function
        mock_llm_fn.assert_called_once_with(step1_data, mock_openai_client)
        mock_fallback_fn.assert_not_called()
        assert result == {"functional_dna": "openai result"}

    def test_openai_generalization_fallback_on_error(self):
        """Test that OpenAI generalization falls back on error."""
        mock_llm_fn = MagicMock(side_effect=Exception("LLM Error"))
        mock_fallback_fn = MagicMock(return_value={"functional_dna": "fallback"})
        mock_openai_client = MagicMock()

        strategy = OpenAIGeneralizationStrategy(
            mock_fallback_fn, mock_llm_fn, mock_openai_client
        )

        step1_data = {"analysis": {"summary": "test"}}

        result = strategy.generalize(step1_data)

        # Should fall back
        mock_fallback_fn.assert_called_once_with(step1_data)
        assert result == {"functional_dna": "fallback"}

    def test_openai_generalization_get_name(self):
        """Test that get_name() returns correct name."""
        strategy = OpenAIGeneralizationStrategy(
            MagicMock(), MagicMock(), MagicMock()
        )
        assert strategy.get_name() == "OpenAI GPT Generalization"


class TestClaudeAnalysisStrategy:
    """Test ClaudeAnalysisStrategy."""

    def test_claude_analysis_calls_llm(self):
        """Test that analyze() calls Claude API."""
        mock_claude_client = MagicMock()
        mock_claude_client.analyze_product.return_value = {"summary": "claude result"}
        mock_fallback_fn = MagicMock()

        strategy = ClaudeAnalysisStrategy(mock_fallback_fn, mock_claude_client)

        scraped_data = {"markdown": "# Test\nContent"}
        extracted_data = {"title": "Test Product"}
        url = "https://example.com"

        result = strategy.analyze(scraped_data, extracted_data, url)

        mock_claude_client.analyze_product.assert_called_once()
        mock_fallback_fn.assert_not_called()
        assert result == {"summary": "claude result"}

    def test_claude_analysis_fallback_on_error(self):
        """Test that Claude strategy falls back on error."""
        mock_fallback_fn = MagicMock(return_value={"summary": "fallback result"})
        mock_claude_client = MagicMock()
        mock_claude_client.analyze_product.side_effect = Exception("API Error")

        strategy = ClaudeAnalysisStrategy(mock_fallback_fn, mock_claude_client)

        result = strategy.analyze({"markdown": "# Test"}, {"title": "Test"}, "http://test.com")

        mock_fallback_fn.assert_called_once()
        assert result == {"summary": "fallback result"}

    def test_claude_analysis_get_name(self):
        """Test that get_name() returns correct name."""
        strategy = ClaudeAnalysisStrategy(MagicMock(), MagicMock())
        assert "Claude" in strategy.get_name()
        assert "Default" in strategy.get_name()


class TestClaudeGeneralizationStrategy:
    """Test ClaudeGeneralizationStrategy."""

    def test_claude_generalization_calls_llm_fn(self):
        """Test that generalize() calls the LLM function."""
        mock_llm_fn = MagicMock(return_value={"functional_dna": "claude result"})
        mock_fallback_fn = MagicMock()
        mock_claude_client = MagicMock()

        strategy = ClaudeGeneralizationStrategy(
            mock_fallback_fn, mock_llm_fn, mock_claude_client
        )

        step1_data = {"analysis": {"summary": "test"}}
        result = strategy.generalize(step1_data)

        mock_llm_fn.assert_called_once_with(step1_data, mock_claude_client)
        mock_fallback_fn.assert_not_called()
        assert result == {"functional_dna": "claude result"}

    def test_claude_generalization_fallback_on_error(self):
        """Test that Claude generalization falls back on error."""
        mock_llm_fn = MagicMock(side_effect=Exception("LLM Error"))
        mock_fallback_fn = MagicMock(return_value={"functional_dna": "fallback"})
        mock_claude_client = MagicMock()

        strategy = ClaudeGeneralizationStrategy(
            mock_fallback_fn, mock_llm_fn, mock_claude_client
        )

        step1_data = {"analysis": {"summary": "test"}}
        result = strategy.generalize(step1_data)

        mock_fallback_fn.assert_called_once_with(step1_data)
        assert result == {"functional_dna": "fallback"}

    def test_claude_generalization_get_name(self):
        """Test that get_name() returns correct name."""
        strategy = ClaudeGeneralizationStrategy(
            MagicMock(), MagicMock(), MagicMock()
        )
        assert "Claude" in strategy.get_name()
        assert "Default" in strategy.get_name()
