from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.agent import agent
from app import database, models, crud

# Initialize database
models.Base.metadata.create_all(bind=database.engine)

# Create FastAPI application
app = FastAPI(title="Google Drive Search Agent")


# Request body schema
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None

# Response body schema
class ChatResponse(BaseModel):
    response: str
    session_id: int

class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: str

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str

    class Config:
        from_attributes = True

@app.get("/")
def root():
    return {"message": "Google Drive Search Agent is running!"}

@app.get("/sessions", response_model=List[SessionResponse])
def get_sessions(db: Session = Depends(database.get_db)):
    sessions = crud.get_sessions(db)
    # Format dates
    return [{"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()} for s in sessions]

@app.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
def get_session_messages(session_id: int, db: Session = Depends(database.get_db)):
    messages = crud.get_messages(db, session_id)
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages]

class RenameRequest(BaseModel):
    title: str

@app.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(database.get_db)):
    session = crud.delete_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}

@app.put("/sessions/{session_id}")
def rename_session(session_id: int, request: RenameRequest, db: Session = Depends(database.get_db)):
    session = crud.rename_session(db, session_id, request.title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session renamed", "title": session.title}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(database.get_db)):
    try:
        session_id = request.session_id
        
        # If no session provided, create one
        if not session_id:
            # Generate a simple title from the first message
            title = " ".join(request.message.split()[:5])
            if not title:
                title = "New Chat"
            db_session = crud.create_session(db, title=title)
            session_id = db_session.id
            history = []
        else:
            # Fetch existing history
            history = crud.get_messages(db, session_id)
            
        # Build messages payload
        messages_payload = []
        for msg in history:
            messages_payload.append({
                "role": msg.role,
                "content": msg.content
            })
            
        messages_payload.append({
            "role": "user",
            "content": request.message
        })

        # Save user message to DB
        crud.add_message(db, session_id, role="user", content=request.message)

        result = agent.invoke(
            {
                "messages": messages_payload
            }
        )

        content = result["messages"][-1].content

        if isinstance(content, str):
            final_message = content
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            final_message = "\n".join(text_parts)
        else:
            final_message = str(content)

        # Save agent response to DB
        crud.add_message(db, session_id, role="assistant", content=final_message)

        return ChatResponse(response=final_message, session_id=session_id)

    except Exception as e:
        return ChatResponse(response=f"Error: {str(e)}", session_id=request.session_id or 0)