import asyncio
from agent import ReAct_Agent

async def main():
    active_tools = ["do-nmap"] 
    agent = ReAct_Agent()
    
    print("--- Initializing MCP Stack and LLM ---")
    try:
        await agent.setup(active_tools)
    except Exception as e:
        print(f"Failed to setup agent: {e}")
        return
    
    chat_state = None
     
    print("\n--- Chat Started (Type 'exit' to stop) ---")
    
    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        try:
            
            result = await agent.process_query(
                user_query=user_input,
                conversation_state=chat_state
            )

            chat_state = result["state"]
            

            print("\n--- Agent Response ---")
            print(result["response"])

        except Exception as e:
            print(f"Error: {e}")
    
    print("\n--- Cleaning up resources ---")
    await agent.cleanup()
    logs = result.get("logs", [])
    if logs:
        print("\n--- Execution Logs ---")
        for log in logs:
            print(f"  > {log}")

if __name__ == "__main__":
    asyncio.run(main())