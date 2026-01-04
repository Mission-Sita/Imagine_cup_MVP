import sys
import os
import asyncio
import json
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Fix Path to allow imports from current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import Agents
from backend_ptt import PTTAgent, run_agent
from agent_io import AgentIO

app = FastAPI(title="PTT Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: Dict[str, AgentIO] = {}

class StartRequest(BaseModel):
    goal: str
    target: str
    constraints: dict = {}

class InputRequest(BaseModel):
    data: str

@app.post("/start/{session_id}")
async def start(session_id: str, req: StartRequest):
    if session_id in sessions:
        pass # Overwrite allowed for now

    io = AgentIO()
    sessions[session_id] = io

    agent = PTTAgent(
        goal=req.goal,
        target=req.target,
        constraints=req.constraints,
        io=io,
    )

    asyncio.create_task(run_agent(agent))

    async def stream():
        try:
            while True:
                msg = await io.output_queue.get()
                yield json.dumps(msg) + "\n"
                if msg["type"] == "status" and msg["payload"] == "Agent finished":
                     break
        except asyncio.CancelledError:
            print(f"Client disconnected {session_id}")

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson"
    )

@app.post("/input/{session_id}")
async def input_endpoint(session_id: str, req: InputRequest):
    io = sessions.get(session_id)
    if not io:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await io.input_queue.put(req.data)
    return {"status": "accepted"}

if __name__ == "__main__":
    import uvicorn
    # ⚠️ Run on Port 8001 to distinguish from Chatbot
    uvicorn.run(app, host="0.0.0.0", port=8001)