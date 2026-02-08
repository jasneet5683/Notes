from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TaskInput(BaseModel):
    """Model for creating a new task"""
    task_name: str = Field(..., min_length=1, description="Name of the task")
    assigned_to: str = Field(..., description="Person assigned to the task")
    start_date: str = Field(..., description="Task start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Task end date (YYYY-MM-DD)")
    status: str = Field(default="Not Started", description="Current task status")
    client: str = Field(default="General", description="Client name")
    priority: str = Field(default="Medium", description="Task priority level")

class TaskUpdate(BaseModel):
    """Model for updating task status"""
    task_name: str = Field(..., description="Name of the task to update")
    new_status: str = Field(..., description="New status for the task")

class TaskResponse(BaseModel):
    """Model for task response"""
    task_name: str
    assigned_to: str
    status: str
    priority: str
    client: str

class ChatRequest(BaseModel):
    """Model for chat/AI requests"""
    user_message: str = Field(..., min_length=1, description="User's message")
    conversation_history: Optional[List[str]] = Field(
        default_factory=list, 
        description="Previous chat messages"
    )

class ChatResponse(BaseModel):
    """Model for AI response"""
    response: str
    timestamp: datetime
    status: str = "success"
