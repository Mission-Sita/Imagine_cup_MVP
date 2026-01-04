import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

key = os.getenv("OPEN_AI_API_KEY")
base = os.getenv("OPEN_AI_API_BASE")

print(f"--- API Key Debug ---")
if key:
    print(f"✅ Key Found: {key[:5]}...{key[-3:]}")
    print(f"   Length: {len(key)}")
    print(f"   Has spaces? {'YES ❌' if ' ' in key else 'NO ✅'}")
else:
    print("❌ Key is NONE. Check your .env variable name!")

print(f"API Base: {base}")