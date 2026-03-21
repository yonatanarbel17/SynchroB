"""
Generalization Strategy Pattern: Abstract interface for different generalization methods.
This allows easy switching between direct generalization, LLM-based generalization, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class GeneralizationStrategy(ABC):
    """Abstract base class for generalization strategies."""
    
    @abstractmethod
    def generalize(self, step1_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generalize product data from Step 1 and return Functional DNA.
        
        Args:
            step1_data: Complete Step 1 output dictionary containing:
                - analysis: Analysis results (summary, capabilities, etc.)
                - extracted_data: Raw extracted data
                - url: Original product URL
                - timestamp: Analysis timestamp
            
        Returns:
            Dictionary with generalization results:
                - functional_dna: Comprehensive abstract problem description (abstract_problem, core_algorithm, complexity, input_output_contract, state_management, scalability_pattern, data_flow, concurrency_model, error_handling, performance_characteristics, dependencies, language_agnostic_pattern, mathematical_model)
                - market_reach: Potential industries/use cases (broader categories)
                - friction_report: Integration complexity assessment
                - interface_map: Standardized adapter schema
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this generalization strategy."""
        pass


class DirectGeneralizationStrategy(GeneralizationStrategy):
    """Direct intelligent generalization using pattern matching and heuristics (no LLM)."""

    def __init__(self, generalize_fn):
        """
        Initialize direct generalization strategy.

        Args:
            generalize_fn: Callable that takes step1_data and returns generalization dict.
                           Typically Step2Generalizer._generate_direct_generalization.
        """
        self._generalize_fn = generalize_fn

    def generalize(self, step1_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generalization using intelligent pattern matching."""
        return self._generalize_fn(step1_data)

    def get_name(self) -> str:
        return "Direct Intelligent Generalization"


class GeminiGeneralizationStrategy(GeneralizationStrategy):
    """Generalization using Google Gemini API."""

    def __init__(self, fallback_fn, llm_fn, gemini_client):
        """
        Initialize Gemini generalization strategy.

        Args:
            fallback_fn: Callable for direct generalization fallback
            llm_fn: Callable for LLM generalization (takes step1_data and llm client)
            gemini_client: Initialized GeminiClient instance
        """
        self._fallback_fn = fallback_fn
        self._llm_fn = llm_fn
        self.llm = gemini_client

    def generalize(self, step1_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generalization using Gemini API."""
        try:
            return self._llm_fn(step1_data, self.llm)
        except Exception as e:
            print(f"⚠️  Gemini generalization failed: {str(e)}")
            print("🔄 Falling back to direct intelligent generalization...")
            return self._fallback_fn(step1_data)

    def get_name(self) -> str:
        return "Gemini API Generalization"


class OpenAIGeneralizationStrategy(GeneralizationStrategy):
    """Generalization using OpenAI GPT API."""

    def __init__(self, fallback_fn, llm_fn, openai_client):
        """
        Initialize OpenAI generalization strategy.

        Args:
            fallback_fn: Callable for direct generalization fallback
            llm_fn: Callable for LLM generalization (takes step1_data and llm client)
            openai_client: Initialized OpenAIClient instance
        """
        self._fallback_fn = fallback_fn
        self._llm_fn = llm_fn
        self.llm = openai_client

    def generalize(self, step1_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generalization using OpenAI API."""
        try:
            return self._llm_fn(step1_data, self.llm)
        except Exception as e:
            print(f"⚠️  OpenAI generalization failed: {str(e)}")
            print("🔄 Falling back to direct intelligent generalization...")
            return self._fallback_fn(step1_data)

    def get_name(self) -> str:
        return "OpenAI GPT Generalization"


class ClaudeGeneralizationStrategy(GeneralizationStrategy):
    """Generalization using Anthropic Claude API. The default / go-to strategy."""

    def __init__(self, fallback_fn, llm_fn, claude_client):
        """
        Initialize Claude generalization strategy.

        Args:
            fallback_fn: Callable for direct generalization fallback
            llm_fn: Callable for LLM generalization (takes step1_data and llm client)
            claude_client: Initialized ClaudeClient instance
        """
        self._fallback_fn = fallback_fn
        self._llm_fn = llm_fn
        self.llm = claude_client

    def generalize(self, step1_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generalization using Claude API."""
        try:
            return self._llm_fn(step1_data, self.llm)
        except Exception as e:
            print(f"⚠️  Claude generalization failed: {str(e)}")
            print("🔄 Falling back to direct intelligent generalization...")
            return self._fallback_fn(step1_data)

    def get_name(self) -> str:
        return "Claude API Generalization (Default)"
