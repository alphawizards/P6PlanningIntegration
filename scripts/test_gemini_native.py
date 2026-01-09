
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Load .env explicitly
load_dotenv()

def test_native_gemini():
    print(f"GenAI Version: {genai.__version__}")
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        print("❌ Error: LLM_API_KEY not found in env")
        return

    print(f"Testing Native SDK with Key: {api_key[:5]}...")
    
    try:
        # List models to see what's available
        print("Finding a valid model...")
        models = list(genai.list_models())
        
        valid_model = None
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name and 'flash' in m.name:
                    valid_model = m.name
                    break
        
        if not valid_model:
            # Fallback
            for m in models:
                if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name:
                    valid_model = m.name
                    break
        
        if valid_model:
            print(f"FOUND_MODEL: {valid_model}")
            
            # Test generation
            print(f"Testing with {valid_model}...")
            model = genai.GenerativeModel(valid_model)
            response = model.generate_content("Hello")
            print(f"✅ Success! Response: {response.text}")
        else:
            print("❌ No valid Gemini models found")
        
    except Exception as e:
        print(f"❌ Native SDK Failed: {e}")


if __name__ == "__main__":
    test_native_gemini()
