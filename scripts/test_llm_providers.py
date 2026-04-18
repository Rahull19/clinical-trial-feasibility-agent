"""Test script to verify real LLM provider integrations."""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.llm.openai_provider import OpenAIProvider
from app.llm.groq_provider import GroqProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.xai_provider import XAIProvider

def test_provider(provider_class, api_key_env, provider_name):
    """Test a single LLM provider."""
    print(f"\n{'='*60}")
    print(f"Testing {provider_name}")
    print(f"{'='*60}")
    
    api_key = os.getenv(api_key_env)
    if not api_key:
        print(f"❌ {api_key_env} not found in environment")
        return False
    
    print(f"✓ API key found: {api_key[:20]}...")
    
    try:
        provider = provider_class(api_key=api_key)
        print(f"✓ Provider initialized: {provider.provider_name}")
        print(f"✓ Available: {provider.is_available()}")
        
        # Test with a simple prompt
        prompt = "Say 'Hello from {provider_name}' and nothing else."
        print(f"\nSending test prompt...")
        response = provider.generate(prompt.format(provider_name=provider_name))
        print(f"✓ Response received ({len(response)} chars):")
        print(f"  {response[:200]}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Test all LLM providers."""
    print("\n" + "="*60)
    print("LLM Provider Integration Test")
    print("="*60)
    
    results = {}
    
    # Test OpenAI
    results['OpenAI'] = test_provider(
        OpenAIProvider, 
        'OPENAI_API_KEY', 
        'OpenAI GPT-4o'
    )
    
    # Test Groq
    results['Groq'] = test_provider(
        GroqProvider, 
        'GROQ_API_KEY', 
        'Groq Llama'
    )
    
    # Test Gemini
    results['Gemini'] = test_provider(
        GeminiProvider, 
        'GEMINI_API_KEY', 
        'Google Gemini'
    )
    
    # Test xAI
    results['xAI'] = test_provider(
        XAIProvider, 
        'XAI_API_KEY', 
        'xAI Grok'
    )
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for provider, success in results.items():
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"{provider:15} {status}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} providers working")

if __name__ == "__main__":
    main()
