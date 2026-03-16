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
                            "target_month": {"type": "string", "description": "The month number (e.g., '3' for March). Return as a string."},
                            "target_year": {"type": "string", "description": "The year (e.g., '2026'). Return as a string."},
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
                            "target_month": {"type": "string", "description": "The month number (e.g., '3' for March). Return as a string."},
                            "target_year": {"type": "string", "description": "The year (e.g., '2026'). Return as a string."}
                        },
                        "required": ["request_analysis", "group_by"] # Make it required
                    }
                }
            }
            #rest of the tools can be pasted here
        ]

        system_prompt = f"""You are a PMP certified smart project management assistant. 
            Today's Date: {today_date}
            TASK LIST:
            {tasks_context}

            ### PROTOCOL:
            1. **LISTEN**: Identify if the user needs an action (add/update) or information (view/stats).
            2. Understand the intent of the user
            3. **ANALYZE**: Fill `request_analysis` with your plan.
            4. **ACT**: Call the specific tool, If the user wants to update or add something, you **MUST** call the relevant tool. 
            5. **REPORT**: AFTER the tool runs, you MUST summarize the result for the user.

            ### YOUR TOOLS:
            - 'update_task_field': Modify data.
            - 'send_project_email': Send emails.
            - 'check_schedule_conflicts': Check logic.
            - 'filter_tasks_by_date': only when filetr is requested Filter by Month/Date.
            - 'get_task_statistics': Get counts for charts.
            - Answer general questions normally

            ### CRITICAL INSTRUCTIONS FOR RESPONSE:
            - **DO NOT** write the function name in your chat response (e.g., do not write 'function:update_task_field'). 
            - If you use a tool, stay silent until the tool returns data, then explain the result to the user.
            - When updating priority, use "High", "Medium", or "Low".
            - If the tool returns a list of tasks, format them nicely as a Markdown table.
            - If the tool returns "No tasks found", tell the user exactly that.
            - If the user requests flowchart, gantt charts, mind maps check mermaid rules.
            ### TASK EXTRACTION RULES:
            When a user wants to add a task, generate the TASK_PREVIEW_JSON block but DO NOT call the add_to_sheet function/tool yet.
            If the user does not specify a start date, only then you must automatically set "start_date" to the today's date {today_date}.
            If the user provides a date (e.g., "Starting Monday" or "On June 1st"), use that date only.
            NEVER generate more than one task JSON block for a single request unless the user explicitly asks for multiple tasks.
            Wait for the user to click the 'Confirm' button in the interface."
            TASK_PREVIEW_JSON:
            {{
              "ui_type": "TASK_ADDITION" ,
              "task_name": "extracted name",
              "start_date": "YYYY-MM-DD",
              "end_date": "YYYY-MM-DD",
              "status": "Pending",
              "assigned_to": "extracted name",
              "client": "extracted client",
              "priority": "Medium",
              "predecessor": ""
            }}
            - Today's date is {today_date}. Use this to calculate relative dates.
            - After providing the JSON, ask the user: "I've prepared the task details above. Should I add this to the tracker?"
            ### VISUALIZATION RULES (STRICT):
            1. **FOR CHARTS (Bar/Pie/Line)**:
               - Call `get_task_statistics` first.
               - Wrap the output in a ```json block as established.
               -**IMPORTANT:** Output valid JSON only. Do not use double curly braces {{ }}. Use single {{ }}.
                FORMAT FOR CHART:
            ```json
                {{
                    "is_chart": true,
                    "chart_type": "bar",
                    "title": "Tasks by Status",
                    "data": {{
                        "labels": ["Done", "Pending"],
                        "values": [5, 2]
                    }},
                    "summary": "Here is the chart showing task distribution."
                }}
                ```
            2. **FOR DIAGRAMS (Flowcharts/Gantt)**:
               - Use the current TASK LIST provided above.
               - Wrap the code exactly in a ```mermaid block.
            ### CRITICAL MERMAID RULES:
            1. TYPE SELECTION: 
            - Use 'graph TD' for Flowcharts/Processes.
            - Use 'gantt' for Timelines/Schedules.
            - NEVER mix them (e.g., NO 'section' inside a 'graph').

            2. FLOWCHART SYNTAX (graph TD):
            - Format: NodeID["Label Text"]
            - Always put each relationship on a NEW LINE.
            - Example:
                 graph TD
                 A["Start"] --> B["Task 1"]
                 B --> C["Finish"]

            3. GANTT SYNTAX (gantt):
            - Use 'section' only here.
            - Format: Task Name :active, des1, 2024-01-01, 3d
   
            4. NO SPECIAL CHARACTERS: Avoid using parentheses () or extra quotes "" inside the labels. Use square brackets [] for all labels.               
            """
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            for msg in conversation_history[-5:]:
                messages.append({"role": "user", "content": str(msg)})
        
        messages.append({"role": "user", "content": str(user_message)})
        
        # --- 1. FIRST API CALL ---
        print("🔹 Sending request to OpenAI...", flush=True)
        response = client.chat.completions.create(
            model="qwen-2.5-coder-32b-instruct",
            #model="llama-3.3-70b-versatile",
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

                    #elif function_name == "get_tasks_due_soon":
                    #    # We pass the 'tasks' list we fetched at the top of the main function
                    #    # We also pass the 'days' argument from the AI (defaults to 15 if missing)
                    #    days_arg = args.get("days", 15)
                    #    function_response = get_tasks_due_soon(tasks, days=days_arg)    
                    
                    #Function calls here

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


            # --- 3. SECOND API CALL (The Fix) ---
            print("🔹 Generating final answer...", flush=True)
            
            second_response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                # remove tools=tools  <-- IMPORTANT: Don't pass tools here
                # remove tool_choice="auto" <-- IMPORTANT: Don't pass this here
                temperature=0.7 # Slight increase to make it conversational
            )
            
            final_answer = second_response.choices[0].message.content.strip()
            return final_answer if final_answer else "✅ Action completed."
        # ==========================================================
        # ✅ THE MISSING PART: Handle responses that DON'T use tools
        # ==========================================================
        if response_message.content:
            return response_message.content.strip()
        
        return "I processed your request, but I don't have a specific text response for you."

        
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
        
        # Get the actual current date and year
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        current_year = now.year
        # 🔹 IMPROVED PROMPT
        # We use f-strings for BOTH and explicitly tell it the year
        system_content = (
            f"You are a PMP certified senior project management expert. "
            f"IMPORTANT: Today is {today_str}. The current year is {current_year}. "
            f"Provide a concise executive summary with key metrics and insights."
        )
        user_content = (
            f"Summarize the project status based on these tasks:\n{tasks_context}\n\n"
            f"LOGIC RULES:\n"
            f"1. Today's Date is {today_str}.\n"
            f"2. A task is ONLY 'Overdue' if its end_date is BEFORE {today_str}.\n"
            f"3. If a task is due in {current_year + 1} or {current_year + 2}, it is 'Upcoming', NOT 'Overdue'.\n"
            f"4. Do not hallucinate dates."
        )
        response = client.chat.completions.create(
            # 💡 Use the 70b model for summaries if possible, it's much better at logic
            model="llama-3.1-8b-instant",
            #model="allam-2-7b",
            #model="llama-3.3-70b-versatile", 
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1, # Lower temperature = less hallucination
            max_tokens=500
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
