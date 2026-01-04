from pydantic import BaseModel
from typing import List, Optional, Any

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default_user" 

class ChatResponse(BaseModel):
    response: str
    logs: List[str] = [] 