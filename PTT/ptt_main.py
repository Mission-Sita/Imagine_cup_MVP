import asyncio
from ptt_agent import PTTAgent

async def main():
    agent = PTTAgent(
        goal="scan example.com for basic information",
        target="example.com",
        constraints={
            "Number_of_tasks":"Try to reach goal in less task"
            }
    )

    await agent.setup()
    await agent.initialize_tree()
    await agent.run_reasoning_loop()
    await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
