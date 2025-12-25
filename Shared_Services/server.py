import sys
from mcp.server.fastmcp import FastMCP
from vector_db import VectorDBManager

# 1. Create the MCP Server
mcp = FastMCP("Security-Brain")

# 🔍 HELPER: Send logs to stderr so we don't break the MCP protocol
def log(message):
    print(f"[Advait-Log] {message}", file=sys.stderr)

# 2. Initialize the Database
# We wrap this in a try-block to catch errors early
try:
    log("🧠 Initializing Vector DB connection...")
    db = VectorDBManager()
    log("✅ Vector DB Connected!")
except Exception as e:
    log(f"❌ FATAL ERROR: Could not connect to DB. {e}")
    # We continue, but the tool will fail if called
    db = None 

@mcp.tool()
def consult_security_knowledge_base(query: str) -> str:
    """
    CRITICAL: Use this tool FIRST for any questions about payloads, syntax, or vulnerability definitions.
    
    Do NOT hallucinate payloads. Always check this knowledge base.
    
    Capabilities:
    1. Returns exact syntax for attacks (SQLi, XSS, etc.) from the 'PayloadsAllTheThings' library.
    2. Explains how specific vulnerabilities work.
    3. Provides context on security concepts.
    
    Args:
      query ((str): The specific question (e.g., "Give me a time-based SQL injection payload for MySQL").
    """
    log(f"📨 Received Query: '{query}'")
    
    if db is None:
        return "Error: Database is not connected. Check server logs."

    try:
        # Search the brain
        results = db.search_memory(query, top_k=3)
        
        if not results:
            return "No specific payloads found in knowledge base."
        
        # Format for the Agent
        response = f"Found {len(results)} relevant entries:\n"
        for i, doc in enumerate(results):
            # Clean up filename for display
            source = doc.metadata.get('source', 'Unknown').split('\\')[-1]
            response += f"\n--- Entry {i+1} (Source: {source}) ---\n"
            response += f"{doc.page_content[:1000]}...\n"
            
        return response

    except Exception as e:
        log(f"Database Error: {e}")
        return f"Database Error: {e}"

if __name__ == "__main__":
    # This starts the server
    log("✅ MCP Server is ready and listening...")
    mcp.run()