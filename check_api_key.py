"""Quick check of API key configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('ANTHROPIC_API_KEY', '')
max_rpm = os.getenv('AGENT_MAX_RPM', 'not set')

if api_key:
    print(f"✅ API Key loaded: {api_key[:20]}...{api_key[-10:]}")
    print(f"   Length: {len(api_key)} characters")
    print(f"   Starts with: {api_key[:15]}")
else:
    print("❌ NO API KEY FOUND")

print(f"\n📊 Max RPM setting: {max_rpm}")
print(f"   Model: {os.getenv('LLM_MODEL', 'not set')}")
