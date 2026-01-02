import asyncio
import json
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend_ptt import PTTAgent, run_agent
from agent_io import AgentIO

app = FastAPI(title="PTT Agent Streaming API")


sessions: Dict[str, AgentIO] = {}


class StartRequest(BaseModel):
    goal: str
    target: str
    constraints: dict


class InputRequest(BaseModel):
    data: str


@app.post("/start/{session_id}")
async def start_agent(session_id: str, req: StartRequest):
    if session_id in sessions:
        raise HTTPException(status_code=400, detail="Session already exists")

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
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )



@app.post("/input/{session_id}")
async def send_input(session_id: str, body: InputRequest):
    io = sessions.get(session_id)
    if not io:
        raise HTTPException(status_code=404, detail="Invalid session")

    await io.input_queue.put(body.data)
    return {"status": "ok"}
