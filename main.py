import asyncio
from ptt_agent import PTTAgent

async def main():
    agent = PTTAgent(
        goal="gather information about the target 192.168.128.2",
        target="192.168.128.2",
        constraints={"Aggressiveness": "Don't start too aggressive initially"}
    )

    await agent.setup()
    await agent.initialize_tree()
    await agent.run_reasoning_loop()
    await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
