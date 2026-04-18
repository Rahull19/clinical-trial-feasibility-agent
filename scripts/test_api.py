"""Quick test script for the FastAPI endpoint."""

import requests
import os

# Test health endpoint
print("Testing /health endpoint...")
response = requests.get("http://localhost:8000/health")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# Test analyze-trial endpoint
print("Testing /analyze-trial endpoint...")
script_dir = os.path.dirname(os.path.abspath(__file__))
protocol_path = os.path.join(script_dir, "test_protocol.json")

with open(protocol_path, "rb") as f:
    files = {"file": ("test_protocol.json", f, "application/json")}
    data = {"llm_provider": "openai"}
    response = requests.post("http://localhost:8000/analyze-trial", files=files, data=data)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"LLM Provider: {result.get('llm_provider')}")
    print(f"Status: {result.get('status')}")
    print(f"Recommendation: {result.get('recommendation', {}).get('recommendation')}")
    print(f"Feasibility Score: {result.get('recommendation', {}).get('feasibility_score')}")
else:
    print(f"Error: {response.text}")
