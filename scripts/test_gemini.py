
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config.settings import LLM_API_KEY, LLM_PROVIDER, LLM_MODEL
from src.ai.llm_client import LLMClient

def test_gemini_connection():
    print(f"Testing connectivity for Provider: {LLM_PROVIDER}")
    print(f"Model: {LLM_MODEL}")
    
    if not LLM_API_KEY:
        print("❌ Error: LLM_API_KEY is not set!")
        return
        
    print(f"API Key present: {LLM_API_KEY[:4]}...{LLM_API_KEY[-4:]}")
    
    try:
        client = LLMClient()
        response = client.chat([{"role": "user", "content": "Hello! Just confirming you are working. Reply with 'Confirmed'."}])
        print(f"✅ Success! Response: {response}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_gemini_connection()
