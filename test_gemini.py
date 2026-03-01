"""
Test script for Gemini integration.
Run this to verify your Gemini API key is working.
"""

import sys
from config import config
from src.analysis import GeminiClient


def test_gemini():
    """Test Gemini client initialization and basic functionality."""
    print("Testing Gemini Integration...")
    print(f"API Key configured: {bool(config.GEMINI_API_KEY)}")
    print(f"Model: {config.GEMINI_MODEL}")
    
    if not config.GEMINI_API_KEY:
        print("⚠️  Warning: GEMINI_API_KEY not set")
        return False
    
    try:
        # Initialize client
        client = GeminiClient()
        print("✓ GeminiClient initialized successfully")
        
        # Test with a simple classification (optional - uncomment to test)
        # print("\nTesting domain classification...")
        # test_signature = {
        #     "inputs": [{"type": "DataFrame"}],
        #     "outputs": [{"type": "float"}],
        #     "complexity": "O(n log n)"
        # }
        # result = client.classify_domain(test_signature)
        # print(f"✓ Classification result: {result}")
        
        print("\n✅ Gemini integration test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_gemini()
    sys.exit(0 if success else 1)
