"""
Configuration module for SynchroB.
Loads API keys and configuration from environment variables.

All API keys must be set in the .env file. See env.example for reference.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # OpenAI API Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")  # Default to GPT-4o (or use gpt-4-turbo, gpt-3.5-turbo)
    
    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash")  # Default to Gemini 2.0 Flash
    
    # Firecrawl API Configuration
    FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
    
    @classmethod
    def validate(cls):
        """Validate that required API keys are set."""
        missing_keys = []
        
        # OpenAI is optional (can use Gemini instead)
        # if not cls.OPENAI_API_KEY:
        #     missing_keys.append("OPENAI_API_KEY")
        
        if not cls.FIRECRAWL_API_KEY:
            missing_keys.append("FIRECRAWL_API_KEY")
        
        # At least one LLM API key should be set
        if not cls.OPENAI_API_KEY and not cls.GEMINI_API_KEY:
            missing_keys.append("OPENAI_API_KEY or GEMINI_API_KEY")
        
        if missing_keys:
            raise ValueError(
                f"Missing required API keys: {', '.join(missing_keys)}\n"
                "Please set them in your .env file. See .env.example for reference."
            )
        
        return True


# Create a config instance
config = Config()
