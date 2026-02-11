import os
import json
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY
from services.google_sheets_service import (
    fetch_all_tasks, 
    update_task_field, 
    add_task_from_ai
)
from typing import List, Optional

client = OpenAI(api_key=OPENAI_API_KEY)

def format_tasks_for_context(tasks: List) -> str:
    """Format tasks into a readable context string with complete information"""
    if not tasks:
        return "No tasks found in the system."
    
    formatted_tasks = []
    for task in tasks:
        # UPDATED: Added Start Date, End Date, and Client
        task_info = (
            f"• Task: {task.get('Task_Name', 'Unknown')} | "
            f"Assigned: {task.get('assigned_to', 'Unassigned')} | "
            f"Status: {task.get('status', 'Unknown')} | "
            f"End Date: {task.get('end_date', 'N/A')} | " 
            f"Start Date: {task.get('start_date', 'N/A')} | "
            f"Client: {task.get('Client', 'N/A')} | " 
            f"Priority: {task.get('Priority', 'N/A')}"
        )
        formatted_tasks.append(task_info)
    
    return f"Current Tasks in System:\n" + "\n".join(formatted_tasks)

def filter_tasks_by_assignee(tasks: List, assignee_name: str) -> List:
    """Filter tasks for a specific assignee (case-insensitive)"""
    filtered_tasks = []
    assignee_lower = assignee_name.lower().strip()
    
    for task in tasks:
        # UPDATED: Changed 'Assigned To' to 'assigned_to'
        assigned_to = task.get('assigned_to', '').lower().strip()
        if assigned_to == assignee_lower:
            filtered_tasks.append(task)
    
    return filtered_tasks

def generate_ai_response(
    user_message: str, 
    conversation_history: Optional[List[str]] = None
) -> str:
    """Generate AI response using OpenAI API with Tool Calling capabilities"""
    try:
        # Fetch current tasks for context
        tasks = fetch_all_tasks()
        tasks_context = format_tasks_for_context(tasks)
        
        # Get Today's Date
        today_date = datetime.now().strftime("%Y-%m-%d")

        # --- TOOL 1 Update Task ---
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "update_task_field",
                    "description": "Update a specific detail (status, priority, assigned_to, end_date) of a project task.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_name": {"type": "string", "description": "The exact name of the task."},
                            "field_type": {"type": "string", "enum": ["status", "priority", "assigned_to", "end_date"]},
                            "new_value": {"type": "string", "description": "The new value to set."}
                        },
                        "required": ["task_name", "field_type", "new_value"]
                    }
                }
            }
        ]

         # Tool 2: Add Task
            {
                "type": "function",
                "function": {
                    "name": "add_task_to_sheet",
                    "description": "Add a brand new task to the project tracker.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_name": {"type": "string", "description": "The name of the new task."},
                            "assigned_to": {"type": "string", "description": "Who is responsible? Default to 'Unassigned' if not specified."},
                            "priority": {"type": "string", "enum": ["Low", "Medium", "High"], "description": "Priority level. Default 'Medium'."},
                            "end_date": {"type": "string", "description": "Due date in YYYY-MM-DD format. Leave empty if not specified."}
                            "client": {"type": "string", "enum": ["DU UAE", "Etisalat", "Batelco"], "description": "Client Name. Leave empty if not specified."},
                        },
                        "required": ["task_name"]
                    }
                }
            }
        ]

        
        # Enhanced system prompt with DATE AWARENESS + TOOL INSTRUCTIONS
        system_prompt = f"""You are a helpful project management assistant. 
        
        CONTEXT:
        Today's Date: {today_date}
        
        TASK LIST:
        {tasks_context}
        
        INSTRUCTIONS:
        - Search through the task list carefully.
        - When users ask about dates (e.g., "due soon", "next 10 days"), compare the 'End Date' in the list with 'Today's Date'.
        - If the user asks about specific people, match names case-insensitively.
        - If a user explicitly asks to CHANGE or UPDATE a task (e.g., "Mark X as Done", "Assign Y to John"), use the 'update_task_field' tool.
        - Be specific. If a task is overdue, mention that.
        """
        
        # Build conversation messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-5:]:
                messages.append({"role": "user", "content": str(msg)})
        
        # Add current user message
        messages.append({"role": "user", "content": str(user_message)})
        
        # --- 1. FIRST API CALL (Check for tools) ---
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            tools=tools,           # <--- Added Tools
            tool_choice="auto",    # <--- Let AI decide
            temperature=0.3,
            max_tokens=500
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # --- 2. HANDLE TOOL CALLS (If AI wants to update something) ---
        if tool_calls:
            # Append AI's intent to history so it knows it tried to call a function
            messages.append(response_message)

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                # Case 1: Update Task
                if function_name == "update_task_field":
                    # Parse arguments
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute Python Function
                    function_response = update_task_field(
                        task_name=function_args.get("task_name"),
                        field_type=function_args.get("field_type"),
                        new_value=function_args.get("new_value")
                    )

                # CASE 2: ADD TASK
                elif function_name == "add_task_to_sheet":
                    # Make sure to import add_task_to_sheet at the top of the file!
                    function_response = add_task_to_sheet(
                        task_name=args.get("task_name"),
                        assigned_to=args.get("assigned_to", "Unassigned"),
                        priority=args.get("priority", "Medium"),
                        end_date=args.get("end_date", "")
                    )
                    # Append Result to Conversation
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })

            # --- 3. SECOND API CALL (Get final confirmation text) ---
            second_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            return second_response.choices[0].message.content.strip()

        # If no tool was called, return original response
        return response_message.content.strip()
        
    except Exception as e:
        print(f"❌ Error generating AI response: {e}")
        return "Sorry, I couldn't generate a response at this moment. Please try again."

def get_tasks_by_assignee(assignee_name: str) -> str:
    """Get tasks for a specific assignee - useful for direct queries"""
    try:
        all_tasks = fetch_all_tasks()
        user_tasks = filter_tasks_by_assignee(all_tasks, assignee_name)
        
        if not user_tasks:
            # UPDATED: Changed 'Assigned To' to 'assigned_to'
            assignees = {task.get('assigned_to', '').strip() for task in all_tasks if task.get('assigned_to')}
            
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
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error summarizing tasks: {e}")
        return "Unable to generate summary."
