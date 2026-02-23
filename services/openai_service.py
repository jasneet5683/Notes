import os
import json
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY, GROQ_API_KEY
from services.google_sheets_service import (
    fetch_all_tasks, 
    update_task_field, 
    add_task_from_ai,
    filter_tasks_by_date,
    get_task_statistics,
    check_schedule_conflicts,
    get_tasks_due_soon
)
from typing import List, Optional
from services.email_service import send_email_via_brevo
import sys

#client = OpenAI(api_key=OPENAI_API_KEY)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY") 
)

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
        "description": "Update a specific detail of a project task.",
        "parameters": {
            "type": "object",
            "properties": {
                # The AI generates this analysis:
                "request_analysis": {
                    "type": "string", 
                    "description": "A brief summary of WHY this update is being made based on user input."
                },
                "task_name": {
                    "type": "string", 
                    "description": "The exact name of the task."
                },
                "field_type": {
                    "type": "string", 
                    # ✅ ADD "predecessor" HERE
                    "enum": ["status", "priority", "assigned_to", "end_date", "predecessor"]
                },
                "new_value": {
                    "type": "string", 
                    "description": "The new value to set."
                }
            },
            "required": ["request_analysis", "task_name", "field_type", "new_value"]
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
                    # --- NEW FIELD: The Summary lives here ---
                    "request_analysis": {
                        "type": "string", 
                        "description": "A structured summary of the meeting context and action plan."
                    },
                    "task_name": {"type": "string", "description": "The name of the new task."},
                    "assigned_to": {"type": "string", "description": "Who is responsible? Default to 'Unassigned'."},
                    "priority": {"type": "string", "enum": ["Low", "Medium", "High"]},
                    "end_date": {"type": "string", "description": "Due date (YYYY-MM-DD)."},
                    "client": {"type": "string", "enum": ["DU UAE", "Etisalat", "Batelco"]},
                    "predecessor_name": {"type": "string"}
                },
                "required": ["request_analysis", "task_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_schedule_conflicts",
            "description": "Check if any tasks start before their predecessors end.",
            "parameters": {
                "type": "object", 
                "properties": {}, 
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_project_email",
            "description": "Send an email summary or report.",
            "parameters": {
                "type": "object",
                "properties": {
                    # --- NEW FIELD ---
                    "request_analysis": {
                        "type": "string", 
                        "description": "Summary of what is being emailed and to whom."
                    },
                    "recipient_email": {"type": "string"},
                    "subject": {"type": "string"},
                    "email_body": {"type": "string"}
                },
                "required": ["request_analysis", "subject", "email_body"]
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
                            # --- ADD THIS ---
                            "request_analysis": {
                                "type": "string",
                                "description": "Why are we filtering? (e.g., 'Checking tasks for March')."
                            },
                            "target_month": {"type": "integer"},
                            "target_year": {"type": "integer"},
                            "target_date": {"type": "string"}
                        },
                        "required": ["request_analysis"] # Make it required
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
                            # --- ADD THIS ---
                            "request_analysis": {
                                "type": "string",
                                "description": "Summary of the stats request (e.g., 'Analyzing status breakdown')."
                            },
                            "group_by": {"type": "string", "enum": ["status", "priority", "assigned_to", "month"]},
                            "target_month": {"type": "integer"},
                            "target_year": {"type": "integer"}
                        },
                        "required": ["request_analysis", "group_by"] # Make it required
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_tasks_due_soon",
                    "description": "Get a list of tasks due within a specific number of days from today. Use this for questions like 'What is due next week?' or 'Upcoming deadlines'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "request_analysis": {
                                "type": "string",
                                "description": "Why are we checking deadlines? (e.g., 'User asked for next week's tasks')."
                            },
                            "days": {
                                "type": "integer", 
                                "description": "Number of days to look ahead (default is 15).",
                                "default": 15
                            }
                        },
                        "required": ["request_analysis"]
                    }
                }
            }
        ]

        system_prompt = f"""You are an intelligent project management assistant. 
        Today's Date: {today_date}
        TASK LIST:
        {tasks_context}

        ### PROTOCOL: LISTEN -> ANALYZE -> ACT
        1. Listen to the user's meeting notes or request.
        2. Analyze the priority, context, and required actions.
        3. Fill the `request_analysis` field in the tool with your plan.
        4. EXECUTE the appropriate tool.

        ### PHASE 1: LISTEN & ANALYZE (Internal Logic)
        1.  **Detect Intent:** Does the user mention a meeting, a plan, or an urgent issue?
        2.  **Determine Priority:**
            -   **LOW/MEDIUM:** "Shared info", "Planning", "Update", "Routine", "Follow up". (e.g., "Batelco shared info").
            -   **HIGH/CRITICAL:** "Angry", "Escalation", "Urgent", "Blocker", "Deadline missed".
        3.  **Multi-Task Detection (CRITICAL):**
            -   If the user mentions multiple milestones (e.g., "Launch by X, Sign by Y"), you must identify them as **SEPARATE TASKS**.
            -   Do not bundle them into one generic task.
        ### SPECIAL INSTRUCTIONS:
        - **Upcoming Deadlines:** If the user asks "What is due soon?" or "Next 10 days", use the `get_tasks_due_soon` tool. Do NOT guess the dates yourself.
        - **Specific Dates:** If the user asks for "Tasks in March", use `filter_tasks_by_date`.

        ---
        ### PHASE 2: SUMMARIZE (User Output)
        **BEFORE** calling any tools, you must output a structured summary to the user in this format:
        **📝 Project Update Summary:**
        *   **Context:** [Briefly state the context, e.g., Meeting with Batelco]
        *   **Key Updates:**
            *   [Point 1]
            *   [Point 2]
        *   **Action Plan:** Creating [Number] tasks with [Priority Level] priority.
        ---
        ### PHASE 3: ACT (Tool Execution)
        **IMMEDIATELY** after the summary, generate the tool calls for `add_task`.
        **Rules for Tool Calls:**
        1.  **Split Tasks:** If Phase 1 identified multiple dates/items, call `add_task_from_ai` multiple times (Parallel Function Calling).
        2.  **Naming:** Use clear, short names (e.g., "Batelco Launch" instead of "They are planning to launch").
        3.  **Assignee:** Apply the assignee (e.g., Jasneet) to ALL generated tasks if implied.
        4.  **Dates:** Standardize to YYYY-MM-DD.
         - **DEPENDENCIES:**
           - If the user says "after [Task A]", set 'predecessor_name' to [Task A].
        - **SCHEDULE CHECKS:**
           - If asked "Is my schedule okay?", call 'check_schedule_conflicts'.
        ### Stats LOGIC:
        - For "how many", "stats", or "percentage", use `get_task_statistics`.
        - For specific lists of tasks, use `filter_tasks_by_date`.
        ####FORMATTING RULES:
        1. **NEVER** use the XML format like `<function=...>`.
        2. **ALWAYS** generate a standard JSON Tool Call.
        3. **ALWAYS** fill the `request_analysis` field.
        #### Critical Visualization Rules
        - TABLES: If the user wants a list, output a Markdown Table.
        - If the user asks for a stats/chart, call 'get_task_statistics' first. hen, STRICTLY at the end of your response, output the JSON wrapped in `chart` tags like this:
            Here is your summary text...
            ```chart
            {{
              "type": "chart_data",
              "labels": ["Done", "Pending"],
              "datasets": [{{ "data": [10, 5] }}]
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
            model="llama-3.3-70b-versatile",
            #model="llama-3.1-8b-instant",
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

                if args is None:
                    args = {} 
                # --- NEW STEP: EXTRACT & PRINT SUMMARY ---
                # We use .pop() to get the summary AND remove it from 'args'
                # so it doesn't crash the actual python function later.
                ai_analysis = args.pop("request_analysis", None)

                if ai_analysis:
                    print(f"\n📝 **AI ANALYSIS:** {ai_analysis}")
                    print("-" * 40, flush=True)

                # --- EXECUTE THE ACTUAL FUNCTION ---
                function_response = "Error: Unknown function."

                try:
                    if function_name == "add_task_from_ai":
                        # We pass **args because 'request_analysis' is already removed
                        function_response = add_task_from_ai(**args)

                    elif function_name == "update_task_field":
                        # Call the function
                        result_dict = update_task_field(**args)
                        # Extract just the message string for the AI to read
                        # If we don't do this, the AI might get confused receiving a raw JSON object
                        function_response = result_dict["message"]

                    elif function_name == "check_schedule_conflicts":
                        function_response = check_schedule_conflicts() # No args needed

                    elif function_name == "send_project_email":
                        function_response = send_project_email(**args)

                    elif function_name == "filter_tasks_by_date":
                        function_response = filter_tasks_by_date(**args)

                    elif function_name == "get_task_statistics":
                        function_response = get_task_statistics(**args)

                    elif function_name == "get_tasks_due_soon":
                        # We pass the 'tasks' list we fetched at the top of the main function
                        # We also pass the 'days' argument from the AI (defaults to 15 if missing)
                        days_arg = args.get("days", 15)
                        function_response = get_tasks_due_soon(tasks, days=days_arg)

                    # Convert response to string for the LLM
                    function_response = str(function_response)
                    
                except Exception as e:
                    error_msg = f"Error executing {function_name}: {str(e)}"
                    print(f"❌ EXECUTION ERROR: {error_msg}", flush=True)
                    function_response = error_msg

                # --- APPEND FUNCTION RESULT TO MESSAGE HISTORY ---
                messages.append(
                    {
                        "tool_call_id": tool_id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )


            # --- 3. SECOND API CALL ---
            second_response = client.chat.completions.create(
                #model="llama-3.3-70b-versatile",
                model="llama-3.1-8b-instant",
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
            #model="llama-3.3-70b-versatile",
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior project management expert. Provide a concise summary with key metrics, dependencies, and insights highlighting clients for Executive review."
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
            #model="llama-3.3-70b-versatile",
            model="llama-3.1-8b-instant",
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
