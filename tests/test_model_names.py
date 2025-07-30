"""
Quick test to verify OpenAI model names and API response
"""

import os
import requests
import json

def test_openai_models():
    """Test what models are available and what gets charged"""
    
    # Load API key
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OPENAI_API_KEY found")
        return
    
    print("🔍 Testing OpenAI API models...")
    
    # Test different model name formats
    test_models = [
        "gpt-4o-mini",
        "gpt-4o-mini-2024-07-18", 
        "gpt-4-turbo",
        "gpt-4-turbo-preview",
        "gpt-3.5-turbo"
    ]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    base_url = "https://api.openai.com/v1"
    
    for model in test_models:
        print(f"\n🧪 Testing model: {model}")
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Hello, what model are you?"}
            ],
            "max_tokens": 50,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                actual_model = result.get("model", "unknown")
                tokens_used = result["usage"]["total_tokens"]
                
                print(f"   ✅ SUCCESS")
                print(f"   📝 Requested: {model}")
                print(f"   🤖 Actual model: {actual_model}")
                print(f"   💰 Tokens used: {tokens_used}")
            else:
                print(f"   ❌ ERROR: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")

if __name__ == "__main__":
    test_openai_models()
