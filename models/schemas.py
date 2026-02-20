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
    predecessor: Optional[str] ="" 

#class TaskUpdate(BaseModel):
#    """Model for updating task status"""
#    task_name: str = Field(..., description="Name of the task to update")
#    new_status: str = Field(..., description="New status for the task")

class TaskUpdate(BaseModel):
    """
    Model for updating task details. 
    Fields are optional so you can update just one at a time.
    """
    # We don't strictly need task_name here since it's in the URL (/tasks/{task_name}),
    # but we can keep it if you prefer.
    task_name: Optional[str] = Field(None, description="Name of the task (optional in body if in URL)")
    
    # Make these Optional so you aren't forced to send them if you don't want to change them
    new_status: Optional[str] = Field(None, description="New status (e.g., Done, In Progress)")
    new_predecessor: Optional[str] = Field(None, description="New predecessor task name")
    new_priority: Optional[str] = Field(None, description="New priority (High, Medium, Low)")
    new_end_date: Optional[str] = Field(None, description="New deadline/end date")


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
