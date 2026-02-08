import os
from openai import OpenAI
from config import OPENAI_API_KEY
from services.google_sheets_service import fetch_all_tasks
from typing import List, Optional

client = OpenAI(api_key=OPENAI_API_KEY)

def format_tasks_for_context(tasks: List) -> str:
    """Format tasks into a readable context string with complete information"""
    if not tasks:
        return "No tasks found in the system."
    
    formatted_tasks = []
    for task in tasks:
        # Include assignee information in the formatting
        task_info = (
            f"• Task: {task.get('Task Name', 'Unknown')} | "
            f"Assigned to: {task.get('Assigned To', 'Unassigned')} | "
            f"Status: {task.get('Status', 'Unknown')} | "
            f"Priority: {task.get('Priority', 'N/A')}"
        )
        formatted_tasks.append(task_info)
    
    return f"Current Tasks in System:\n" + "\n".join(formatted_tasks)

def filter_tasks_by_assignee(tasks: List, assignee_name: str) -> List:
    """Filter tasks for a specific assignee (case-insensitive)"""
    filtered_tasks = []
    assignee_lower = assignee_name.lower().strip()
    
    for task in tasks:
        assigned_to = task.get('Assigned To', '').lower().strip()
        if assigned_to == assignee_lower:
            filtered_tasks.append(task)
    
    return filtered_tasks

def generate_ai_response(
    user_message: str, 
    conversation_history: Optional[List[str]] = None
) -> str:
    """Generate AI response using OpenAI API"""
    try:
        # Fetch current tasks for context
        tasks = fetch_all_tasks()
        tasks_context = format_tasks_for_context(tasks)
        
        # Enhanced system prompt with better task understanding
        system_prompt = f"""You are a helpful project management assistant. Help users with their project tasks and status updates.

When users ask about tasks assigned to specific people:
- Search through the task list carefully
- Match names case-insensitively (e.g., "Ady", "ady", "ADY" should all match)
- If tasks are found, list them clearly
- If no tasks are found, double-check the assignee names and suggest similar matches

{tasks_context}

Guidelines for responses:
- Be specific about task details when listing them
- If asking about a person's tasks, show ALL tasks assigned to that person
- If no exact match is found, suggest checking spelling or list available assignees
"""
        
        # Build conversation messages
        messages = [
            {"role": "system", "content": system_prompt}
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
            temperature=0.3,  # Lower temperature for more consistent responses
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"❌ Error generating AI response: {e}")
        return "Sorry, I couldn't generate a response at this moment. Please try again."

def get_tasks_by_assignee(assignee_name: str) -> str:
    """Get tasks for a specific assignee - useful for direct queries"""
    try:
        all_tasks = fetch_all_tasks()
        user_tasks = filter_tasks_by_assignee(all_tasks, assignee_name)
        
        if not user_tasks:
            # Get list of all assignees to suggest alternatives
            assignees = set()
            for task in all_tasks:
                assigned_to = task.get('Assigned To', '').strip()
                if assigned_to:
                    assignees.add(assigned_to)
            
            suggestion = f"Available assignees: {', '.join(sorted(assignees))}" if assignees else ""
            return f"No tasks found assigned to '{assignee_name}'. {suggestion}"
        
        return format_tasks_for_context(user_tasks)
        
    except Exception as e:
        print(f"❌ Error fetching tasks by assignee: {e}")
        return f"Error retrieving tasks for {assignee_name}"

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
                    "content": "You are a project management expert. Provide a concise summary with key metrics and insights."
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
