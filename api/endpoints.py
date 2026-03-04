from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import JSONResponse

# Removed ChatRequest and ChatResponse from imports to avoid conflict with local definitions
from models.schemas import (
    TaskInput, TaskUpdate, TaskResponse
)
from services.google_sheets_service import (
    fetch_all_tasks, add_task_to_sheet, 
    update_task_status, search_tasks,
    update_task_field
)
from services.openai_service import (
    generate_ai_response, 
    summarize_tasks,
    simple_ai_chat
)

# ✅ DATA MODELS

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    prompt: str 
    conversation_history: Optional[List[ChatMessage]] = None

class ChatResponse(BaseModel):
    response: str
    timestamp: datetime
    status: str = "success" 

class SimpleAskRequest(BaseModel):
    question: str


router = APIRouter(prefix="/api", tags=["tasks"])

# ✅ TASK MANAGEMENT ENDPOINTS

@router.get("/tasks", response_model=dict)
def get_all_tasks():
    """Retrieve all tasks from the spreadsheet"""
    tasks = fetch_all_tasks()
    return {
        "count": len(tasks),
        "tasks": tasks,
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }

@router.post("/tasks", response_model=dict)
def create_task(task: TaskInput):
    """Add a new task to the spreadsheet"""
    if not add_task_to_sheet(task):
        raise HTTPException(
            status_code=500, 
            detail="Failed to add task to spreadsheet"
        )
    return {
        "message": f"✅ Task '{task.task_name}' added successfully!",
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }

@router.put("/tasks/{task_name}", response_model=dict)
def update_task(task_name: str, update: TaskUpdate):
    """
    Update a task. Handles multiple fields (status, predecessor, priority) 
    by calling the service layer for each one found.
    """
    
    updates_made = []
    errors = []
    # 1. Check for Status Update
    if update.new_status:
        result = update_task_field(task_name, "status", update.new_status)
        if result["success"]:
            updates_made.append(f"Status -> {update.new_status}")
        else:
            errors.append(result["message"])
    # 2. Check for Predecessor Update
    if update.new_predecessor is not None:
        # Note: We check is not None to allow clearing it with empty string
        result = update_task_field(task_name, "predecessor", update.new_predecessor)
        if result["success"]:
            updates_made.append(f"Predecessor -> {update.new_predecessor}")
        else:
            errors.append(result["message"])
    # 3. Check for Priority Update (if you added this to TaskUpdate schema)
    # if update.new_priority:
    #     result = update_task_field(task_name, "priority", update.new_priority)
    #     ...
    # --- Construct Final Response ---
    
    if errors and not updates_made:
        # If everything failed
        raise HTTPException(status_code=400, detail="; ".join(errors))
    
    if not updates_made and not errors:
         return {"message": "⚠️ No changes detected or provided."}
    return {
        "message": f"✅ Task '{task_name}' updated: " + ", ".join(updates_made),
        "errors": errors if errors else None,
        "status": "success"
    }


@router.get("/tasks/search", response_model=dict)
def search_all_tasks(query: str = Query(..., min_length=1)):
    """Search for tasks by name or assigned person"""
    results = search_tasks(query)
    return {
        "query": query,
        "count": len(results),
        "results": results,
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }

# ✅ AI CHAT ENDPOINTS

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Ensure all history items are strings to prevent type errors
        # This rebuilds the list ensuring 'content' is strictly a string
        conversation_history = [
            ChatMessage(role=msg.role, content=str(msg.content)) 
            for msg in (request.conversation_history or [])
        ]

        # Generate AI response
        response_text = generate_ai_response(
            user_message=request.prompt,
            conversation_history=conversation_history
        )
        
        # Return structured response with timestamp
        return ChatResponse(
            response=response_text,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        # Log the actual error for debugging
        print(f"Error in chat endpoint: {e}") 
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Processing error", 
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.get("/summary", response_model=dict)
def get_project_summary():
    """Get an AI-generated summary of all project tasks"""
    summary = summarize_tasks()
    return {
        "summary": summary,
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }

# ✅ SIMPLE ASK ENDPOINT (For Summaries with Hard Facts)

@router.post("/ask", response_model=dict)
def ask_simple_question(request: SimpleAskRequest):
    """
    Receives a prompt (with calculated stats) and returns a text answer.
    """
    try:
        answer = simple_ai_chat(request.question)
        return {
            "answer": answer,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ HEALTH CHECK

@router.get("/health", response_model=dict)
def health_check():
    """Check if the API is running"""
    return {
        "status": "Online",
        "service": "Application",
        "timestamp": datetime.now().isoformat()
    }
