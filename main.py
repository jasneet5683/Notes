import os
import json
import gspread
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Project Status Chat Agent")

# CORS configuration for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= GOOGLE SHEETS SETUP =============
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", 
        scope
    )
    gs_client = gspread.authorize(creds)
    sheet = gs_client.open("Task_Manager").sheet1
except Exception as e:
    print(f"Error connecting to Google Sheets: {e}")
    sheet = None

# ============= OPENAI SETUP =============
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============= DATA MODELS =============
class ChatRequest(BaseModel):
    user_message: str
    conversation_history: list = []

class TaskInput(BaseModel):
    task_name: str
    assigned_to: str
    start_date: str
    end_date: str
    status: str
    client: str = "General"
    priority: str = "Medium"

class TaskUpdate(BaseModel):
    task_name: str
    new_status: str

# ============= HELPER FUNCTIONS =============
def fetch_all_tasks():
    """Fetch all tasks from Google Sheet and return as list of dicts"""
    try:
        if sheet is None:
            raise Exception("Google Sheets connection not initialized")
        
        records = sheet.get_all_records()
        return records
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return []

def format_tasks_for_context(tasks):
    """Format task data for AI context"""
    if not tasks:
        return "No tasks found in the project."
    
    formatted = "**Current Project Tasks:**\n"
    for i, task in enumerate(tasks, 1):
        formatted += f"\n{i}. Task: {task.get('Task Name', 'N/A')}\n"
        formatted += f"   Assigned to: {task.get('Assigned To', 'N/A')}\n"
        formatted += f"   Status: {task.get('Status', 'N/A')}\n"
        formatted += f"   Start Date: {task.get('Start Date', 'N/A')}\n"
        formatted += f"   End Date: {task.get('End Date', 'N/A')}\n"
        formatted += f"   Client: {task.get('Client', 'N/A')}\n"
    
    return formatted

def generate_ai_response(user_message, tasks_context, conversation_history):
    """Generate intelligent response using OpenAI"""
    system_prompt = f"""You are an intelligent project status assistant. Your role is to:
1. Provide clear, concise updates about project status
2. Answer questions about specific tasks
3. Identify blockers, delays, or issues
4. Suggest next steps or recommendations
5. Maintain a professional and helpful tone

You have access to the following project information:
{tasks_context}

Based on this data and user inquiries, provide insightful responses."""

    # Build message history for context
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add previous conversation history if provided
    for msg in conversation_history[-6:]:  # Keep last 6 messages for context
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {str(e)}"

# ============= API ENDPOINTS =============

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "Project Status Chat Agent is running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/tasks")
def get_all_tasks():
    """Fetch all tasks from Google Sheet"""
    tasks = fetch_all_tasks()
    return {
        "count": len(tasks),
        "tasks": tasks,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/status-summary")
def get_status_summary():
    """Get a quick summary of project status"""
    tasks = fetch_all_tasks()
    
    if not tasks:
        return {"summary": "No tasks available"}
    
    status_breakdown = {}
    for task in tasks:
        status = task.get("Status", "Unknown")
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
    
    return {
        "total_tasks": len(tasks),
        "status_breakdown": status_breakdown,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/chat")
async def chat_with_agent(request: ChatRequest):
    """
    Main chat endpoint for project status inquiries
    
    Example prompts:
    - "What's the current project status?"
    - "Which tasks are overdue?"
    - "Tell me about tasks assigned to John"
    - "What are the blockers?"
    """
    try:
        # Fetch latest tasks
        tasks = fetch_all_tasks()
        tasks_context = format_tasks_for_context(tasks)
        
        # Generate AI response
        ai_response = generate_ai_response(
            request.user_message,
            tasks_context,
            request.conversation_history
        )
        
        return {
            "user_message": request.user_message,
            "agent_response": ai_response,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/add-task")
def add_task(task: TaskInput):
    """Add a new task to the Google Sheet"""
    try:
        if sheet is None:
            raise Exception("Google Sheets not connected")
        
        new_row = [
            task.task_name,
            task.assigned_to,
            task.start_date,
            task.end_date,
            task.status,
            task.client,
            task.priority,
            datetime.now().isoformat()
        ]
        
        sheet.append_row(new_row)
        
        return {
            "message": f"Task '{task.task_name}' added successfully!",
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/update-task")
def update_task_status(update: TaskUpdate):
    """Update the status of an existing task"""
    try:
        if sheet is None:
            raise Exception("Google Sheets not connected")
        
        # Find and update task
        tasks = sheet.get_all_records()
        for i, task in enumerate(tasks, 2):  # Start from 2 (row 1 is header)
            if task.get("Task Name") == update.task_name:
                sheet.update_cell(i, 5, update.new_status)  # Assuming Status is column 5
                return {
                    "message": f"Task '{update.task_name}' updated to '{update.new_status}'",
                    "status": "success"
                }
        
        raise HTTPException(status_code=404, detail=f"Task '{update.task_name}' not found")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
