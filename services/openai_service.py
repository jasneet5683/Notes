import os
from openai import OpenAI
from config import OPENAI_API_KEY
from services.google_sheets_service import fetch_all_tasks
from typing import List, Optional

client = OpenAI(api_key=OPENAI_API_KEY)

def format_tasks_for_context(tasks: List) -> str:
    """Format tasks into a readable context string"""
    if not tasks:
        return "No tasks found in the system."
    
    task_list = "\n".join([
        f"• {task.get('Task Name', 'Unknown')} - {task.get('Status', 'Unknown')} (Priority: {task.get('Priority', 'N/A')})"
        for task in tasks
    ])
    return f"Current Tasks:\n{task_list}"

def generate_ai_response(
    user_message: str, 
    conversation_history: Optional[List[str]] = None
) -> str:
    """Generate AI response using OpenAI API"""
    try:
        # Fetch current tasks for context
        tasks = fetch_all_tasks()
        tasks_context = format_tasks_for_context(tasks)
        
        # Build conversation messages
        messages = [
            {
                "role": "system",
                "content": f"You are a helpful project management assistant. Help users with their project tasks and status updates.\n\n{tasks_context}"
            }
        ]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                messages.append({"role": "user", "content": msg})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Error generating AI response: {e}")
        return "Sorry, I couldn't generate a response at this moment."

def summarize_tasks() -> str:
    """Generate a summary of all project tasks"""
    try:
        tasks = fetch_all_tasks()
        tasks_context = format_tasks_for_context(tasks)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a project management expert. Provide a concise summary."
                },
                {
                    "role": "user",
                    "content": f"Summarize the project status based on these tasks:\n{tasks_context}"
                }
            ],
            temperature=0.5,
            max_tokens=300
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Error summarizing tasks: {e}")
        return "Unable to generate summary."
