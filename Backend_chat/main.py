import os
import sys
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.abspath(os.path.join(current_dir,".."))
chatbot_dir = os.path.join(project_dir,"ChatBot")

sys.path.append(project_dir)
sys.path.append(chatbot_dir)

from ChatBot.agent import ReAct_Agent
from models import ChatRequest, ChatResponse

sessions={}
agent_instance = None

@asynccontextmanager

async def lifespan(app:FastAPI):
    global agent_instance
    print("Initializing Agent and MCP tools")
    agent_instance = ReAct_Agent()
    active_tools = ["do-nmap", "consult_security_knowledge_base", "consult_sql_injection_knowledge_base"]
    try:
        await agent_instance.setup(active_tools=None)
        print("Agent is ready and waiting for call!")
    except Exception as e:
        print(f"Error while seting up the agent:{e}")
    
    yield

    print("Shuting down the agent")
    if agent_instance:
        await agent_instance.cleanup()
    print("Cleanup is complete")

app = FastAPI(title="Pentesting Chatbot",version="1.0",lifespan=lifespan)

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"]
                   )

@app.get("/")
async def health_check():
    return {"status":"online","message":"Chatbot is running"}

@app.post("/chat",response_model=ChatResponse)
async def chat_endpoints(request:ChatRequest):
    global agent_instance
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent is not initialized yet.")
    print(f"Message from {request.thread_id}:{request.message}")
    current_state = sessions.get(request.thread_id, None)

    try:
        result = await agent_instance.process_query(user_query=request.message, conversation_state=current_state)
        sessions[request.thread_id]=result["state"]
        return ChatResponse(response=result["response"],logs=result.get("logs", []))
    except Exception as e:
        print(f"Error processing request {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/chat/{thread_id}")
async def clear_history(thread_id:str):
    
    if thread_id in sessions:
        del sessions[thread_id]
        return {"message": f"Memory cleared for {thread_id}"}
    return {"message": "No memory found to clear."}

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port = 8000)
