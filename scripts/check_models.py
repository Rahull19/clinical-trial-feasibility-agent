"""Check available models for Gemini and xAI."""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Check Gemini models
print("Checking Gemini models...")
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    models = genai.list_models()
    print("\nAvailable Gemini models:")
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(f"  - {model.name}")
except Exception as e:
    print(f"Error: {e}")

# Check xAI models
print("\n\nChecking xAI models...")
try:
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv('XAI_API_KEY'),
        base_url="https://api.x.ai/v1"
    )
    models = client.models.list()
    print("\nAvailable xAI models:")
    for model in models.data:
        print(f"  - {model.id}")
except Exception as e:
    print(f"Error: {e}")
