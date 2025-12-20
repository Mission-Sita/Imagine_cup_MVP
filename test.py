import requests
import json
import threading
import time

BASE_URL = "http://127.0.0.1:9876"

# ---- SSE LISTENER ----
def sse_listener(session_holder):
    print("[*] Connecting to SSE...")
    resp = requests.get(
        BASE_URL,
        headers={"Accept": "text/event-stream"},
        stream=True,
    )
    resp.raise_for_status()

    event = None

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue

        if line.startswith("event:"):
            event = line.split("event:", 1)[1].strip()

        elif line.startswith("data:"):
            data = line.split("data:", 1)[1].strip()

            print(f"[SSE] {event}: {data}")

            # First message gives sessionId
            if event == "endpoint" and "sessionId" not in session_holder:
                session_holder["sessionId"] = data.replace("?sessionId=", "")
                print("[+] sessionId captured")

            # MCP responses come as JSON here
            if event == "message":
                try:
                    msg = json.loads(data)
                    print("\n[MCP RESPONSE]")
                    print(json.dumps(msg, indent=2))
                except json.JSONDecodeError:
                    pass


# ---- MCP POST ----
def send_mcp(session_id, payload):
    url = f"{BASE_URL}/?sessionId={session_id}"
    r = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json=payload,
    )
    r.raise_for_status()
    print("[>] MCP request sent:", payload["method"])


if __name__ == "__main__":
    session = {}

    # Start SSE listener
    t = threading.Thread(target=sse_listener, args=(session,), daemon=True)
    t.start()

    # Wait for sessionId
    while "sessionId" not in session:
        time.sleep(0.1)

    sid = session["sessionId"]

    # ---- STEP 2: tools/list ----
    send_mcp(
        sid,
        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/list",
            "params": {}
        }
    )

    time.sleep(2)

    # ---- STEP 3: example tool call ----
    send_mcp(
        sid,
        {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/call",
            "params": {
                "name": "burp.scan",   # example tool
                "arguments": {
                    "target": "http://example.com"
                }
            }
        }
    )

    print("[✓] Done. Keep running to receive SSE messages.")
    while True:
        time.sleep(1)
