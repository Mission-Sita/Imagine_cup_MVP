from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import json
from datetime import datetime
import traceback


from backend_ptt import PTTAgent
from agent_io import AgentIO


async def run_agent(agent: PTTAgent):
    """Run PTT Agent with error handling"""
    try:
        await agent.setup()
        await agent.initialize_tree()
        await agent.run_reasoning_loop()
        await agent.io.output("status", "Agent finished")
    except Exception as e:
        await agent.io.output("error", f"Error: {str(e)}")
        traceback.print_exc()
    finally:
        await agent.close()

app = FastAPI(title="PTT CyberSec Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mango-glacier-012d66b00.6.azurestaticapps.net"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


sessions: Dict[str, Dict[str, Any]] = {}



class StartAgentRequest(BaseModel):
    session_id: str
    goal: str
    target: str
    constraints: Dict[str, Any] = {}

class SendInputRequest(BaseModel):
    session_id: str
    data: str



@app.get("/")
def root():
    return {
        "status": "running",
        "message": "PTT CyberSec Assistant API",
        "version": "1.0.0"
    }

@app.post("/api/agent/start")
async def start_agent_endpoint(req: StartAgentRequest):
    """Start PTT Agent"""
    session_id = req.session_id
    
    if session_id in sessions:
        raise HTTPException(status_code=400, detail="Session already exists")
    

    io = AgentIO()
    

    agent = PTTAgent(
        goal=req.goal,
        target=req.target,
        constraints=req.constraints,
        io=io
    )
    
 
    sessions[session_id] = {
        "agent": agent,
        "io": io,
        "started_at": datetime.now().isoformat(),
        "status": "running"
    }
    

    asyncio.create_task(run_agent(agent))
    
    return {
        "success": True,
        "session_id": session_id,
        "message": "PTT Agent started"
    }

@app.get("/api/agent/stream/{session_id}")
async def stream_agent_output(session_id: str):
    """Stream agent output using Server-Sent Events"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    io = sessions[session_id]["io"]
    
    async def event_generator():
        try:
            while True:
                msg = await io.output_queue.get()
                yield f"data: {json.dumps(msg)}\n\n"
                
                if msg.get("type") == "status" and "finished" in str(msg.get("payload", "")).lower():
                    break
                    
        except Exception as e:
            error_msg = {"type": "error", "payload": str(e)}
            yield f"data: {json.dumps(error_msg)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@app.post("/api/agent/input")
async def send_agent_input(req: SendInputRequest):
    """Send user input to agent"""
    if req.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    io = sessions[req.session_id]["io"]
    await io.input_queue.put(req.data)
    
    return {"success": True, "message": "Input sent"}

@app.delete("/api/agent/stop/{session_id}")
async def stop_agent_endpoint(session_id: str):
    """Stop PTT Agent"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    agent = session["agent"]
    
    try:
        await agent.close()
    except Exception as e:
        print(f"Error closing agent: {e}")
    
    del sessions[session_id]
    return {"success": True, "message": "Agent stopped"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "active_sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting PTT Backend Server...")
    print("📡 API running on: http://localhost:8000")
    print("📋 Docs available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
