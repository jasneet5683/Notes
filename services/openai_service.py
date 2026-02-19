import os
import json
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY
from services.google_sheets_service import (
    fetch_all_tasks, 
    update_task_field, 
    add_task_from_ai,
    filter_tasks_by_date,
    get_task_statistics,
    check_schedule_conflicts
)
from typing import List, Optional
from services.email_service import send_email_via_brevo
import sys

client = OpenAI(api_key=OPENAI_API_KEY)

def format_tasks_for_context(tasks: List) -> str:
    """Format tasks into a readable context string with complete information"""
    if not tasks:
        return "No tasks found in the system."
    
    formatted_tasks = []
    for task in tasks:
        # 1. Get the Predecessor value safely
        pred_val = str(task.get('predecessor', task.get('successor', ''))).strip()
        if not pred_val or pred_val.lower() == 'none':
            pred_val = "None"

        # 2. UPDATED String Format
        # We added [ID: ...] at the start and | Predecessor: ... at the end
        task_info = (
            f"• [ID: {task.get('task_id', 'N/A')}] "  # <--- CRITICAL: Added ID so AI can link tasks
            f"Task: {task.get('Task_Name', 'Unknown')} | "
            f"Assigned: {task.get('assigned_to', 'Unassigned')} | "
            f"Status: {task.get('status', 'Unknown')} | "
            f"End Date: {task.get('end_date', 'N/A')} | " 
            f"Start Date: {task.get('start_date', 'N/A')} | "
            f"Client: {task.get('Client', 'N/A')} | " 
            f"Priority: {task.get('Priority', 'N/A')} | "
            f"Predecessor ID: {pred_val}"  # <--- CRITICAL: Added Dependency
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
                    "name": "add_task_from_ai",
                    "description": "Add a brand new task to the project tracker.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_name": {"type": "string", "description": "The name of the new task."},
                            "assigned_to": {"type": "string", "description": "Who is responsible? Default to 'Unassigned'."},
                            "priority": {"type": "string", "enum": ["Low", "Medium", "High"], "description": "Priority level."},
                            "end_date": {"type": "string", "description": "Due date (YYYY-MM-DD)."},
                            "client": {"type": "string", "enum": ["DU UAE", "Etisalat", "Batelco"], "description": "Client Name."},
                            # --- NEW FIELD ADDED HERE ---
                            "predecessor_name": {"type": "string", "description": "The name of the task that this new task must come AFTER (dependency)."}
                        },
                        "required": ["task_name"]
                    }
                }
            },
            # --- NEW TOOL FOR CONFLICT CHECKING ---
            {
                "type": "function",
                "function": {
                    "name": "check_schedule_conflicts",
                    "description": "Check if any tasks start before their predecessors end (dependency conflicts).",
                    "parameters": {
                        "type": "object",
                        "properties": {}, # No arguments needed
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_project_email",
                    "description": "Send an email. Use this when the user asks to email a summary, report, or notification.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient_email": {"type": "string", "description": "The email address."},
                            "subject": {"type": "string", "description": "The subject line."},
                            "email_body": {"type": "string", "description": "The full content."}
                        },
                        "required": ["subject", "email_body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "filter_tasks_by_date",
                    "description": "Filter and list tasks based on a specific month, year, or exact date.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_month": {"type": "integer"},
                            "target_year": {"type": "integer"},
                            "target_date": {"type": "string"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_task_statistics",
                    "description": "Get counts of tasks for graphs.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "group_by": {"type": "string", "enum": ["status", "priority", "assigned_to", "month"]},
                            "target_month": {"type": "integer"},
                            "target_year": {"type": "integer"}
                        },
                        "required": ["group_by"]
                    }
                }
            }
        ]

        system_prompt = f"""You are an intelligent project management assistant. 
        Today's Date: {today_date}
        TASK LIST:
        {tasks_context}

        ### CORE OPERATING MODE: LISTEN -> SUMMARIZE -> ACTION ###
        **STEP 1: LISTEN & ANALYZE (Sentiment & Intent)**
        - **Context:** Identify the client/project (e.g., "Batelco").
        - **Sentiment/Priority:**
            - "Bad meeting", "Angry", "Urgent", "Blocker" -> **Priority: HIGH/CRITICAL**
            - "Shared info", "Planning", "Routine", "Update" -> **Priority: LOW/MEDIUM**
        - **Identify Actions:** look for keywords like "start by", "launch by", "sign by".
            - *CRITICAL:* If the user lists multiple dates/items (e.g., "Launch 30-March, Sign 10-April"), you **MUST** identify them as **SEPARATE TASKS**.
        **STEP 2: SUMMARIZE (The Output)**
        Before executing tools, you must output a "Plan of Action" in this HTML format:
        <div class="summary-box">
          <b>📝 Summary of Request:</b>
          <ul>
            <li><b>Context:</b> [e.g., Batelco Business Update]</li>
            <li><b>Detected Sentiment:</b> [e.g., Routine Info (Low Priority)]</li>
            <li><b>Identified Tasks:</b>
                <ul>
                    <li>Task 1: [Name] (Due: [Date])</li>
                    <li>Task 2: [Name] (Due: [Date])</li>
                </ul>
            </li>
            <li><b>Assignee:</b> [Name]</li>
          </ul>
        </div>
        **STEP 3: ACTION (The Tool Calls)**
        - **Generate Function Calls:** 
          - Call `add_task` for **EACH** item identified in Step 1.
          - **DO NOT** combine them into one task.
          - **DO NOT** skip the second task.
          - **Predecessor:** If not explicitly mentioned, pass an empty string `""`.
          - **Dates:** Convert to 'YYYY-MM-DD'.
        **EXAMPLE SCENARIO:**
        Input: "Batelco launch 30-March, Sign 10-April. Assign Jasneet."
        Logic:
        1. Priority = Medium (Planning).
        2. Task 1 = "Batelco Launch" (Due: 2024-03-30).
        3. Task 2 = "Batelco Sign-off" (Due: 2024-04-10).
        4. Assignee = "Jasneet" (Applies to ALL).
        Action: Call `add_task` TWICE.
        - **HANDLING DATA & DEFAULTS (CRITICAL):**
               - **Dates:** Convert "7-March" or "Next Friday" to 'YYYY-MM-DD'.
               - **Predecessor/Dependency:** This is **OPTIONAL**. 
                    - If the user DOES NOT say "after [Task]" or "depends on [Task]", **pass an empty string ("")** to the tool. 
                    - **DO NOT** ask the user for a predecessor. Just add the task.
        - **DEPENDENCIES:**
           - If the user says "after [Task A]", set 'predecessor_name' to [Task A].
        - **SCHEDULE CHECKS:**
           - If asked "Is my schedule okay?", call 'check_schedule_conflicts'.
        FORMATTING RULES:
        1. TABLES: If the user wants a list, output a Markdown Table.
        2. GRAPHS: If the user asks for a chart, call 'get_task_statistics' first. 
           Then output the data in this EXACT JSON format inside a code block:
       ```chart
       {{
         "type": "bar",
         "data": {{
           "labels": ["Pending", "Done", "InProgress"],
           "datasets": [{{
             "label": "Task Status",
             "data": [5, 3, 2],
           }}]
         }}
       }}
       ```
      """ 
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            for msg in conversation_history[-5:]:
                messages.append({"role": "user", "content": str(msg)})
        
        messages.append({"role": "user", "content": str(user_message)})
        
        # --- 1. FIRST API CALL ---
        print("🔹 Sending request to OpenAI...", flush=True)
        response = client.chat.completions.create(
            model="gpt-4", 
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
                
                print(f"🔹 AI CALLED FUNCTION: {function_name}", flush=True)
                
                try:
                    args = json.loads(tool_call.function.arguments)
                except Exception as json_err:
                    print(f"❌ JSON Parse Error: {json_err}", flush=True)
                    args = {}
                
                function_response = "Error: Unknown function." 

                # EXECUTE PYTHON CODE
                try:
                    if function_name == "update_task_field":
                        function_response = update_task_field(
                            task_name=args.get("task_name"),
                            field_type=args.get("field_type"),
                            new_value=args.get("new_value")
                        )
                    
                    elif function_name == "add_task_from_ai":
                        # --- UPDATED ARGUMENTS HERE ---
                        function_response = add_task_from_ai(
                            task_name=args.get("task_name"),
                            assigned_to=args.get("assigned_to", "Unassigned"),
                            priority=args.get("priority", "Medium"),
                            end_date=args.get("end_date", ""),
                            client=args.get("client", "General"),
                            predecessor_name=args.get("predecessor_name", "") # <--- PASSING THE NEW ARG
                        )

                    elif function_name == "check_schedule_conflicts":
                        # --- NEW FUNCTION CALL ---
                        function_response = check_schedule_conflicts()
                        
                    elif function_name == "send_project_email":
                        function_response = send_email_via_brevo(
                            subject=args.get("subject"),
                            email_body=args.get("email_body"),
                            recipient_email=args.get("recipient_email")
                        )

                    elif function_name == "filter_tasks_by_date":
                        function_response = filter_tasks_by_date(
                            target_month=args.get("target_month"),
                            target_year=args.get("target_year"),
                            target_date=args.get("target_date")
                        )

                    elif function_name == "get_task_statistics":
                        function_response = get_task_statistics(
                            group_by=args.get("group_by"),
                            target_month=args.get("target_month"),
                            target_year=args.get("target_year")
                        )
                        
                    else:
                        function_response = f"Error: Function {function_name} not found."

                except Exception as e:
                    print(f"❌ EXECUTION ERROR: {e}", flush=True)
                    function_response = f"Error executing tool: {str(e)}"
                
                # APPEND RESULT
                messages.append({
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response),
                })

            # --- 3. SECOND API CALL ---
            second_response = client.chat.completions.create(
                model="gpt-4",
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
            model="gpt-4",
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

def simple_ai_chat(user_prompt: str) -> str:
    """
    A simple direct chat function. 
    It trusts the prompt provided by the frontend (which includes the accurate counts).
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful project assistant. user will provide data stats, you simply analyze them."},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error in simple_ai_chat: {e}")
        return "I'm sorry, I couldn't process the summary request."
