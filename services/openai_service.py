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
import sys

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
    """Generate AI response using OpenAI API with DEBUGGING enabled"""
    try:
        # Fetch current tasks for context
        tasks = fetch_all_tasks()
        tasks_context = format_tasks_for_context(tasks)
        today_date = datetime.now().strftime("%Y-%m-%d")
        # --- TOOL DEFINITIONS ---
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
            },
            {
                "type": "function",
                "function": {
                    "name": "add_task_from_ai", # <--- Ensure this name is used below
                    "description": "Add a brand new task to the project tracker.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_name": {"type": "string", "description": "The name of the new task."},
                            "assigned_to": {"type": "string", "description": "Who is responsible? Default to 'Unassigned'."},
                            "priority": {"type": "string", "enum": ["Low", "Medium", "High"], "description": "Priority level."},
                            "end_date": {"type": "string", "description": "Due date (YYYY-MM-DD)."},
                            "client": {"type": "string", "enum": ["DU UAE", "Etisalat", "Batelco"], "description": "Client Name."}
                        },
                        "required": ["task_name"]
                    }
                }
            }
        ]
        system_prompt = f"""You are a helpful project management assistant. 
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
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            for msg in conversation_history[-5:]:
                messages.append({"role": "user", "content": str(msg)})
        
        messages.append({"role": "user", "content": str(user_message)})
        
        # --- 1. FIRST API CALL ---
        print("🔹 Sending request to OpenAI...", flush=True)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.3
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        # --- 2. HANDLE TOOL CALLS ---
        if tool_calls:
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                tool_id = tool_call.id
                
                # Force print to Railway logs
                print(f"🔹 AI CALLED FUNCTION: {function_name}", flush=True)
                print(f"🔹 ARGS: {tool_call.function.arguments}", flush=True)
                try:
                    args = json.loads(tool_call.function.arguments)
                except Exception as json_err:
                    print(f"❌ JSON Parse Error: {json_err}", flush=True)
                    args = {}
                function_response = "Error: Unknown function." # Default
                # EXECUTE PYTHON CODE
                try:
                    if function_name == "update_task_field":
                        function_response = update_task_field(
                            task_name=args.get("task_name"),
                            field_type=args.get("field_type"),
                            new_value=args.get("new_value")
                        )
                    
                    # CHECK FOR BOTH NAMES TO PREVENT ERRORS
                    elif function_name == "add_task_from_ai" or function_name == "add_task_to_sheet":
                        function_response = add_task_from_ai(
                            task_name=args.get("task_name"),
                            assigned_to=args.get("assigned_to", "Unassigned"),
                            priority=args.get("priority", "Medium"),
                            end_date=args.get("end_date", ""),
                            client=args.get("client", "General")
                        )
                    else:
                        print(f"❌ NAME MISMATCH: AI called '{function_name}' but Python expects 'add_task_from_ai'", flush=True)
                        function_response = f"Error: Function {function_name} not found."
                except Exception as e:
                    print(f"❌ EXECUTION ERROR: {e}", flush=True)
                    function_response = f"Error executing tool: {str(e)}"
                print(f"🔹 FUNCTION RESULT: {function_response}", flush=True)
                # APPEND RESULT
                messages.append({
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response),
                })
            # --- 3. SECOND API CALL ---
            second_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            return second_response.choices[0].message.content.strip()
        return response_message.content.strip()
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}", flush=True)
        return "Sorry, I encountered a system error."

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
