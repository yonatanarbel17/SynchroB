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
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file at the project root
_project_root = Path(__file__).resolve().parent
load_dotenv(_project_root / ".env", override=True)


class Config:
    """Application configuration.

    Uses properties so that values are read from os.environ at access time,
    AFTER load_dotenv() has populated the environment.
    """

    @property
    def ANTHROPIC_API_KEY(self):
        return os.getenv("ANTHROPIC_API_KEY")

    @property
    def CLAUDE_MODEL(self):
        return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    @property
    def OPENAI_API_KEY(self):
        return os.getenv("OPENAI_API_KEY")

    @property
    def OPENAI_MODEL(self):
        return os.getenv("OPENAI_MODEL", "gpt-4o")

    @property
    def GEMINI_API_KEY(self):
        return os.getenv("GEMINI_API_KEY")

    @property
    def GEMINI_MODEL(self):
        return os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash")

    @property
    def FIRECRAWL_API_KEY(self):
        return os.getenv("FIRECRAWL_API_KEY")

    @property
    def GITHUB_TOKEN(self):
        return os.getenv("GITHUB_TOKEN")

    def validate(self, multi_source: bool = False):
        """
        Validate that required API keys are set.

        Args:
            multi_source: If True, Firecrawl is optional (multi-source discovery
                         can work with LLM + package registries + GitHub alone).
        """
        missing_keys = []

        # In multi-source mode, Firecrawl is just one of many sources
        if not multi_source and not self.FIRECRAWL_API_KEY:
            missing_keys.append("FIRECRAWL_API_KEY")

        # At least one LLM API key should be set (Claude preferred)
        if not self.ANTHROPIC_API_KEY and not self.OPENAI_API_KEY and not self.GEMINI_API_KEY:
            missing_keys.append("ANTHROPIC_API_KEY (or OPENAI_API_KEY / GEMINI_API_KEY)")

        if missing_keys:
            raise ValueError(
                f"Missing required API keys: {', '.join(missing_keys)}\n"
                "Please set them in your .env file. See README.md for setup instructions."
            )

        return True


# Create a config instance
config = Config()
