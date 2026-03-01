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
    
    def __init__(self, generalizer):
        """
        Initialize direct generalization strategy.
        
        Args:
            generalizer: Reference to Step2Generalizer for accessing helper methods
        """
        self.generalizer = generalizer
    
    def generalize(self, step1_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generalization using intelligent pattern matching."""
        return self.generalizer._generate_direct_generalization(step1_data)
    
    def get_name(self) -> str:
        return "Direct Intelligent Generalization"


class GeminiGeneralizationStrategy(GeneralizationStrategy):
    """Generalization using Google Gemini API."""
    
    def __init__(self, generalizer, gemini_client):
        """
        Initialize Gemini generalization strategy.
        
        Args:
            generalizer: Reference to Step2Generalizer for accessing helper methods
            gemini_client: Initialized GeminiClient instance
        """
        self.generalizer = generalizer
        self.llm = gemini_client
    
    def generalize(self, step1_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generalization using Gemini API."""
        try:
            return self.generalizer._generate_llm_generalization_gemini(step1_data, self.llm)
        except Exception as e:
            print(f"⚠️  Gemini generalization failed: {str(e)}")
            print("🔄 Falling back to direct intelligent generalization...")
            return self.generalizer._generate_direct_generalization(step1_data)
    
    def get_name(self) -> str:
        return "Gemini API Generalization"


class OpenAIGeneralizationStrategy(GeneralizationStrategy):
    """Generalization using OpenAI GPT API."""
    
    def __init__(self, generalizer, openai_client):
        """
        Initialize OpenAI generalization strategy.
        
        Args:
            generalizer: Reference to Step2Generalizer for accessing helper methods
            openai_client: Initialized OpenAIClient instance
        """
        self.generalizer = generalizer
        self.llm = openai_client
    
    def generalize(self, step1_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generalization using OpenAI API."""
        try:
            return self.generalizer._generate_llm_generalization_openai(step1_data, self.llm)
        except Exception as e:
            print(f"⚠️  OpenAI generalization failed: {str(e)}")
            print("🔄 Falling back to direct intelligent generalization...")
            return self.generalizer._generate_direct_generalization(step1_data)
    
    def get_name(self) -> str:
        return "OpenAI GPT Generalization"
