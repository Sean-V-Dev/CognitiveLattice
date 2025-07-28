import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Key length: {len(api_key)}")
    print(f"Starts with: {'sk-' if api_key.startswith('sk-') else 'different format'}")
else:
    print("No API key found")
