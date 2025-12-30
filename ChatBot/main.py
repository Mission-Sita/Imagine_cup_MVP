from enum import Enum
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel
from agent import ReAct_Agent
from dynamic_enum import load_tool_enum






from enum import Enum
from typing import List
from pydantic import BaseModel
from utils import load_config

def load_tool_enum():
    mcp_servers, _ = load_config()

    return Enum(
        "ToolName",
        {
            name.replace("-", "_").upper(): name
            for name in mcp_servers.keys()
        },
        type=str
    )

# ✅ MUST be at module level


class InitRequest(BaseModel):
    ToolName = load_tool_enum()


class ChatRequest(BaseModel):
    message: str
    state: Optional[dict] = None

class ChatResponse(BaseModel):
    response: str
    state: dict

app = FastAPI()

agent: ReAct_Agent | None = None

@app.post("/init")
async def initialize_agent(payload: InitRequest):
    global agent
    agent = ReAct_Agent()

    await agent.setup(payload.tools)

    return {
        "message": "Agent initialized successfully",
        "active_tools": payload.tools
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    if agent is None:
        return {"response": "Agent not initialized", "state": {}}

    state = payload.state or {}
    if "messages" not in state:
        state["messages"] = []

    result = await agent.process_query(
        user_query=payload.message,
        conversation_state=state
    )

    return {
        "response": result["response"],
        "state": result["state"]
    }


@app.on_event("shutdown")
async def shutdown_event():
    if agent:
        await agent.cleanup()
