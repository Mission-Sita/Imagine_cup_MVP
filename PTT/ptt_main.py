import asyncio
from ptt_agent import PTTAgent

async def main():
    agent = PTTAgent(
        goal="scan basic information on example.com",
        target="example.com",
        constraints={
            }
    )

    await agent.setup()
    await agent.initialize_tree()
    await agent.run_reasoning_loop()
    await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
