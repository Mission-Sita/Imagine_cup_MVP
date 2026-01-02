import asyncio
from typing import Any, Dict

class AgentIO:
    def __init__(self):
        self.output_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self.input_queue: asyncio.Queue[str] = asyncio.Queue()

    async def output(self, type_: str, payload: Any, *, id: str | None = None):
        await self.output_queue.put({
            "type": type_,
            "payload": payload,
            "id": id,
        })

    async def input(self) -> str:
        return await self.input_queue.get()
