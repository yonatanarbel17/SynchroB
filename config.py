"""
Configuration module for SynchroB.
Loads API keys and configuration from environment variables.

All API keys must be set in the .env file. Create a .env file with the following variables:
# ANTHROPIC_API_KEY=your_key_here    (preferred — Claude is the default LLM)
# OPENAI_API_KEY=your_key_here       (fallback)
# GEMINI_API_KEY=your_key_here       (fallback)
# FIRECRAWL_API_KEY=your_key_here
# GITHUB_TOKEN=your_github_token_here  (optional, increases rate limit)
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""

    # Anthropic / Claude API Configuration (DEFAULT — go-to LLM)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    # OpenAI API Configuration (fallback)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Gemini API Configuration (fallback)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash")

    # Firecrawl API Configuration
    FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

    # GitHub Token (optional — increases API rate limit from 60 to 5000 req/hr)
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    @classmethod
    def validate(cls, multi_source: bool = False):
        """
        Validate that required API keys are set.

        Args:
            multi_source: If True, Firecrawl is optional (multi-source discovery
                         can work with LLM + package registries + GitHub alone).
        """
        missing_keys = []

        # In multi-source mode, Firecrawl is just one of many sources
        if not multi_source and not cls.FIRECRAWL_API_KEY:
            missing_keys.append("FIRECRAWL_API_KEY")

        # At least one LLM API key should be set (Claude preferred)
        if not cls.ANTHROPIC_API_KEY and not cls.OPENAI_API_KEY and not cls.GEMINI_API_KEY:
            missing_keys.append("ANTHROPIC_API_KEY (or OPENAI_API_KEY / GEMINI_API_KEY)")

        if missing_keys:
            raise ValueError(
                f"Missing required API keys: {', '.join(missing_keys)}\n"
                "Please set them in your .env file. See README.md for setup instructions."
            )

        return True


# Create a config instance
config = Config()
