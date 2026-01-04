import requests
import json
import sys
import uuid

# CONFIG
BASE_URL = "http://localhost:8001"
# Generate a random session ID each time so we don't get stuck with old memory
SESSION_ID = f"test_{str(uuid.uuid4())[:8]}"

def run_test():
    print(f"🚀 Connecting to PTT Agent at {BASE_URL}...")
    print(f"🆔 Session ID: {SESSION_ID}")

    # --- 1. ASK USER FOR INPUT ---
    print("\n--- Configuration ---")
    target_input = input("🎯 Enter Target (default: scanme.nmap.org): ").strip()
    if not target_input:
        target_input = "scanme.nmap.org"

    print("\n⚡ Choose a Goal:")
    print("1. FAST Scan (Top 100 ports - takes 10 seconds)")
    print("2. DEEP Scan (All ports - takes 30 mins)")
    choice = input("👉 Enter choice (1/2): ").strip()

    if choice == "2":
        goal_input = f"Perform a comprehensive scan of all ports on {target_input}"
    else:
        # We explicitly tell the AI to use --top-ports 100 to force it to be fast
        goal_input = f"Scan the top 100 ports of {target_input} using nmap. Be quick."

    print(f"\n🚀 Starting Mission: {goal_input}...\n")

    # --- 2. START THE AGENT ---
    try:
        response = requests.post(
            f"{BASE_URL}/start/{SESSION_ID}",
            json={
                "goal": goal_input,
                "target": target_input,
                "constraints": {"scope": "external"}
            },
            stream=True
        )
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("💡 Tip: Is 'python Backend/ptt_api.py' running?")
        return

    print("✅ Connected! Watching Stream...\n")

    # --- 3. LISTEN TO STREAM ---
    try:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                try:
                    data = json.loads(decoded_line)
                    handle_event(data)
                except json.JSONDecodeError:
                    pass       
    except KeyboardInterrupt:
        print("\n🛑 Test Stopped by User.")

def handle_event(data):
    evt_type = data.get("type")
    payload = data.get("payload")

    if evt_type == "log":
        print(f"📝 {payload}")
    
    elif evt_type == "status":
        print(f"ℹ️  {payload}")
        
    elif evt_type == "tool_use":
        print(f"🛠️  Using Tool: {payload['name']}")
        print(f"    Args: {payload['args']}")

    elif evt_type == "error":
        print(f"❌ ERROR: {payload}")

    elif evt_type == "success":
        print(f"\n🎉 SUCCESS! Goal Achieved!\n")

    elif evt_type == "question":
        print(f"\n❓ QUESTION: {payload}")
        user_answer = input("   👉 Your Answer: ")
        send_input(user_answer)
        print("   ✅ Answer sent.\n")

def send_input(user_data):
    url = f"{BASE_URL}/input/{SESSION_ID}"
    try:
        requests.post(url, json={"data": user_data})
    except:
        pass

if __name__ == "__main__":
    run_test()