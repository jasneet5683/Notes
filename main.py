import os
import uvicorn
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

# Import your local modules
from config import Config
from email_service import send_email_via_brevo
from sheet_manager import add_new_task, load_data_global, internal_update_task
#from sheet_manager import add_new_task
from visuals import generate_chart_base64, generate_table_base64
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

#added for Email Attachement support
import matplotlib
matplotlib.use('Agg') # Required for Render/Server usage
import matplotlib.pyplot as plt
import io
import base64

# Initialize FastAPI
app = FastAPI()

# --- CORS Configuration ---
# This allows your HTML frontend (hosted anywhere) to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to your specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Variables ---
excel_text_context = ""
document_loaded = False

# --- Data Models ---
class PromptRequest(BaseModel):
    prompt: str

class TaskRequest(BaseModel):
    task_name: str
    assigned_to: str
    start_date: str
    end_date: str
    status: str
    client: str
    notify_email: str = None  # Optional: specific email to notify immediately

# --- Helper: Team Directory ---
# You can replace this with a database call or a config file lookup
def get_team_directory():
    return {
        "alice": "alice@example.com",
        "bob": "bob@example.com",
        # Add your team members here
    }

# --- Scheduler Logic ---
scheduler = BackgroundScheduler()

def check_deadlines_and_notify():
    """
    Checks Google Sheet for tasks due in 2 days and emails the assignee.
    """
    print("⏰ Scheduler: Checking for upcoming deadlines...")
    sheet = get_google_sheet()
    
    if sheet is None:
        print("❌ Scheduler Error: Can't connect to Google Sheet.")
        return

    try:
        tasks = sheet.get_all_records()
        today = datetime.now().date()
        team_directory = get_team_directory()
        
        for row in tasks:
            # Handle key variations depending on how your headers are named in Sheets
            task_name = row.get("Task Name") or row.get("task_name")
            assigned_to = row.get("Assigned To") or row.get("assigned_to")
            end_date_str = row.get("End Date") or row.get("end_date")
            
            if end_date_str:
                try:
                    # Parse date (Assuming format YYYY-MM-DD)
                    due_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    days_left = (due_date - today).days
                    
                    # Notify if due in exactly 2 days
                    if days_left == 2:
                        # simple match: convert name to lowercase for lookup
                        assignee_email = team_directory.get(assigned_to.lower())
                        
                        if assignee_email:
                            subject = f"🔔 Reminder: '{task_name}' is due soon"
                            body = (
                                f"<h3>Deadline Approaching</h3>"
                                f"<p>Hi {assigned_to}, this is a reminder that the task "
                                f"<strong>{task_name}</strong> is due on <strong>{end_date_str}</strong>.</p>"
                            )
                            send_email_via_brevo(assignee_email, subject, body)
                            print(f"✅ Notification sent to {assignee_email} for task '{task_name}'")
                except ValueError:
                    # Skip rows where date format is invalid
                    continue

    except Exception as e:
        print(f"⚠️ Error during deadline check: {e}")

#----- Helper functoin for loading data


# --- Lifecycle Events ---
@app.on_event("startup")
def startup_event():
    """Runs when the server starts."""
    load_data_global() # Load initial context if needed
    
    # Add the job to the scheduler (runs every day at 9:00 AM)
    scheduler.add_job(check_deadlines_and_notify, 'cron', hour=9, minute=0)
    scheduler.start()
    print("🚀 Background Scheduler Started")

@app.on_event("shutdown")
def shutdown_event():
    """Runs when the server stops."""
    scheduler.shutdown()

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"status": "active", "message": "Backend is running on Railway!"}

@app.post("/api/add-task")
def add_task(task: TaskRequest):
    """
    Receives task data from Frontend, saves to Sheets, and optionally sends an email.
    """
    # 1. Add to Google Sheets
    # Ensure add_new_task in sheet_manager.py accepts these arguments
    result = add_new_task(
        task.task_name, 
        task.assigned_to, 
        task.client, 
        task.end_date
    )
    
    # 2. Send immediate notification if email provided
    if task.notify_email:
        subject = f"New Task Assigned: {task.task_name}"
        body = f"You have been assigned a new task: <strong>{task.task_name}</strong> due on {task.end_date}."
        send_email_via_brevo(task.notify_email, subject, body)

    return {"sheet_response": result, "message": "Task processed successfully"}

@app.get("/api/status")
def get_status():
    global document_loaded, excel_text_context
    if not document_loaded:
        print("⚠️ Data not found in memory, attempting to reload...")
        load_data_global()

    # 2. FAILSAFE: If text exists, force document_loaded to True
    if excel_text_context and len(excel_text_context) > 0:
        document_loaded = True
    
    # 3. Create a safe preview
    if document_loaded and excel_text_context:
        # Show first 100 chars
        data_preview = excel_text_context[:100] + "..."
    else:
        data_preview = "No data loaded."
        
    return {
        "document_loaded": document_loaded,
        "data_preview": excel_text_context[:100] if excel_text_context else "No data loaded"
    }

# ---- Langchain tools
@tool
def update_sheet_tool(task_name: str, field: str, value: str):
    """
    Updates a task in the Google Sheet. 
    Use this tool when the user asks to modify, update, change, or set a value in the tracker.
    """
    print(f"🛠 Tool Triggered: Updating {task_name}...")
    result = internal_update_task(task_name, field, value)
    return result["message"]

@tool
def send_email_tool(to_email: str, subject: str, body: str, attachment_type: str = "none"):
    """
    Sends an email.
    IMPORTANT: 'attachment_type' must be one of: 'chart', 'table', or 'none'.
    - Use 'chart' if user asks for a visualization or graph.
    - Use 'table' if user asks for a list, grid, or table in the email.
    - Use 'none' for standard text emails.
    """
    print(f"📧 Tool Triggered: Sending email to {to_email} with {attachment_type}...")
    
    attachment_data = None
    
    # Decide what to generate based on the AI's request
    if attachment_type.lower() == "chart":
        attachment_data = generate_chart_base64()
    elif attachment_type.lower() == "table":
        attachment_data = generate_table_base64()
    
    # Send the email once
    result = internal_send_email(to_email, subject, body, attachment_data, attachment_type)
    return result["message"]


# --- 8. CHAT AGENT (UPDATED) ---

@app.post("/api/chat")
def chat(request: PromptRequest):
    global excel_text_context
    
    try:
        # 1. Reload data context if missing
        if not document_loaded or not excel_text_context:
            load_data_global()

        # 2. Define Tools
        tools = [update_sheet_tool, send_email_tool]
        tool_map = {
            "update_sheet_tool": update_sheet_tool,
            "send_email_tool": send_email_tool
        }

        # 3. Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o", 
            openai_api_key=openai_key,
            temperature=0
        )
        llm_with_tools = llm.bind_tools(tools)

        # 4. System Prompt
        # NOTE: Double braces {{ }} are used here to escape JSON inside the f-string
        system_msg = f"""
        You are an advanced Project Manager Agent.
        
        CURRENT DATA CONTEXT:
        {excel_text_context}
        
        YOUR TOOLS:
        1. 'update_sheet_tool': Modify data.
        2. 'send_email_tool': Send emails. 
           - PARAMETER 'attachment_type': Set this to 'chart', 'table', or 'none' strictly based on user request.
        
        INSTRUCTIONS:
        - If the user says "Add task [task_name]", call the function responsible for adding a task (e.g., via 'add_task' configured for additions).
        - If the user says "Update task [task_name]", call the function responsible for updating a task (e.g., via 'update_sheet_tool' configured for updates).
        - If the user says "Send email with a CHART", call 'send_email_tool' with attachment_type='chart'.
        - If the user says "Send email with a TABLE", call 'send_email_tool' with attachment_type='table'.
        - If the user says "Send email", use attachment_type='none'.
        - Do NOT call the tool twice.
        - Answer general questions normally.
        - Critical if the users asks to "create action item" or "Add Task", NOT just reply with text. Instead, output a JSON block strictly following this format:  

        FORMAT FOR TASK ADDITION (Output this JSON strictly):
        ```json
        {{
            "action": "add",
            "task_name": "Task Name",
            "assigned_to": "Assignee Name",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "status": "Not Started",
            "client": "Client Name",
            "notify_email": "email@example.com"
        }}
        ```

        FORMAT FOR CHART (For Chat Display Only):
        ```json
        {{ "is_chart": true, "chart_type": "bar", "title": "Tasks by Status", "data": {{ "labels": ["Done", "Pending"], "values": [5, 2] }}, "summary": "Here is the chart." }}
        ```

        FORMAT FOR TABLE (For Chat Display Only):
        ```json
        {{
            "is_table": true,
            "title": "Task Overview",
            "headers": ["Task Name", "Status", "Due Date"],
            "rows": [
                ["Fix Bug", "Done", "2023-10-01"],
                ["Write Docs", "Pending", "2023-10-05"]
            ],
            "summary": "Here is the table you requested."
        }}
        ```
        """

        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content=request.prompt)
        ]

        print("🤖 AI Thinking...")
        ai_response = llm_with_tools.invoke(messages)

        # --- CASE A: TOOL CALLS (LangChain Tools) ---
        if ai_response.tool_calls:
            print(f"🔧 AI decided to use tools: {len(ai_response.tool_calls)}")
            results = []
            
            for tool_call in ai_response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                if tool_name in tool_map:
                    print(f"   -> Executing {tool_name} with args: {tool_args}")
                    tool_output = tool_map[tool_name].invoke(tool_args)
                    results.append(str(tool_output))
                else:
                    results.append(f"Error: Tool {tool_name} not found.")

            # FIXED: Closed the dictionary properly
            return {
                "response": " | ".join(results),
                "type": "text",
                "status": "success"
            }

        # --- CASE B: JSON ACTIONS (Visuals & Add Task) ---
        # Get content cleanly first
        content = ai_response.content.strip()

        if "```json" in content:
            try:
                # Extract clean JSON string
                # FIXED: split() logic adjusted
                clean_json = content.split("```json")[1].split("```")[0].strip()
                data_obj = json.loads(clean_json)
                
                # 1. Handle Charts
                if data_obj.get("is_chart"):
                    return {
                        "response": data_obj.get("summary", "Here is the chart."), 
                        "chart_data": data_obj, 
                        "type": "chart", 
                        "status": "success"
                    }
                
                # 2. Handle Tables
                if data_obj.get("is_table"):
                    return {
                        "response": data_obj.get("summary", "Here is the table."), 
                        "table_data": data_obj, 
                        "type": "table", 
                        "status": "success"
                    }
                
                # 3. Handle Task Addition
                if data_obj.get("action") == "add":
                    print("📝 AI requesting to ADD a new task...")
                    
                    # Extract task details from AI response
                    task_payload = {
                        "task_name": data_obj.get("task_name"),
                        "assigned_to": data_obj.get("assigned_to", "Unassigned"),
                        "start_date": data_obj.get("start_date", ""),
                        "end_date": data_obj.get("end_date", ""),
                        "status": data_obj.get("status", "Not Started"),
                        "client": data_obj.get("client", ""),
                        "notify_email": data_obj.get("notify_email", None)
                    }

                    # Call internal API endpoint
                    api_url = "https://web-production-b8ca4.up.railway.app/api/add-task"
                    
                    sheet_response = requests.post(api_url, json=task_payload)
                    
                    if sheet_response.status_code == 200:
                        return {
                            "response": f"✅ Task '{task_payload['task_name']}' has been successfully added to the Sheet.",
                            "type": "text",
                            "status": "success"
                        }
                    else:
                        return {
                            "response": f"❌ Failed to add task. Server replied: {sheet_response.text}",
                            "type": "text",
                            "status": "error"
                        }

            except json.JSONDecodeError:
                print("⚠️ Failed to parse JSON from AI response.")
            except Exception as e:
                print(f"⚠️ Error processing JSON action: {e}")

        # --- CASE C: STANDARD TEXT RESPONSE ---
        return {
            "response": content,
            "type": "text",
            "status": "success"
        }

    except Exception as e:
        print(f"❌ Chat Error: {e}")
        return {"response": f"Error: {str(e)}", "status": "error"}

# --- Entry Point ---
if __name__ == "__main__":
    # Railway assigns a PORT environment variable. 
    # If not found, it defaults to 8000 (for local testing).
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
