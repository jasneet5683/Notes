from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal
from datetime import datetime


Status = Literal["todo", "in_progress", "done"]
Priority = Literal["low", "medium", "high"]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Status = "todo"
    priority: Priority = "medium"
    due_date: Optional[str] = None  # keep string for simplicity (e.g., "2026-03-01")
    notify_email: Optional[EmailStr] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    due_date: Optional[str] = None


class Task(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: Status
    priority: Priority
    due_date: Optional[str] = None
    created_at: str
    updated_at: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    reply: str


class SummarizeResponse(BaseModel):
    summary: str
    count: int
