import os
import uvicorn
import json
import requests
import pandas as pd
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

# Import your local modules
from config import Config
from email_service import send_email_via_brevo
from sheet_manager import add_new_task, internal_update_task
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

#--------Load Data------------
def load_data_global():
    global excel_text_context, document_loaded
    print("🔄 Loading data from Google Sheets...")
    sheet = Config.get_google_sheet()
    if not sheet:
        document_loaded = False
        return

    try:
        data = sheet.get_all_records()
        if not data:
            print("⚠️ Sheet is empty or couldn't read records.")
            excel_text_context = "No data found."
            document_loaded = True
            return

        df = pd.DataFrame(data)
        df.fillna("N/A", inplace=True)
        
        # Convert dates to string to avoid errors
        for col in df.columns:
            if "date" in col.lower():
                df[col] = df[col].astype(str)

        excel_text_context = df.to_csv(index=False)
        document_loaded = True
        print("✅ Data Successfully Loaded into Memory.")
        # CRITICAL DEBUG: Print the first 100 chars to logs to verify content exists
        print(f"📝 Data Preview in Memory: {excel_text_context[:100]}") 
        
    except Exception as e:
        print(f"❌ Error processing data: {str(e)}")
        document_loaded = False

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
async def startup_event():
    print("🚀 Server Starting...")
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
def add_task_tool(task_name: str, assigned_to: str, client: str, end_date: str, notify_email: str = None):
    """
    Adds a NEW task to the Google Sheet. 
    Required arguments: task_name, assigned_to, client, end_date (YYYY-MM-DD).
    Optional: notify_email.
    """
    print(f"📝 Tool Triggered: Adding task '{task_name}'...")
    
    # Call your existing sheet logic directly
    result = add_new_task(task_name, assigned_to, client, end_date)
    
    # Optional: Send email notification logic here if needed
    if notify_email:
        subject = f"New Task Assigned: {task_name}"
        body = f"You have been assigned: <strong>{task_name}</strong> due on {end_date}."
        send_email_via_brevo(notify_email, subject, body)
        
    return f"Task '{task_name}' added successfully. Sheet response: {result}"

@tool
def update_sheet_tool(task_name: str, field: str, value: str):
    """
    Updates an EXISTING task in the Google Sheet. 
    Use this when user asks to modify status, change dates, or reassign.
    """
    print(f"🛠 Tool Triggered: Updating {task_name}...")
    # Ensure internal_update_task is imported/defined
    result = internal_update_task(task_name, field, value) 
    return str(result)

@tool
def send_email_tool(to_email: str, subject: str, body: str, attachment_type: str = "none"):
    """
    Sends an email via Brevo.
    attachment_type must be: 'chart', 'table', or 'none'.
    """
    print(f"📧 Tool Triggered: Sending email to {to_email}...")
    
    attachment_data = None
    if attachment_type.lower() == "chart":
        attachment_data = generate_chart_base64()
    elif attachment_type.lower() == "table":
        attachment_data = generate_table_base64()
    
    # Ensure this function exists in your email_service.py or is defined locally
    # result = internal_send_email(to_email, subject, body, attachment_data, attachment_type)
    # Using a placeholder for the example:
    send_email_via_brevo(to_email, subject, body) 
    return "Email sent successfully."

#  CHAT AGENT (UPDATED) ---
# UPDATE: Remove 'async' to prevent blocking the event loop with synchronous calls
@app.post("/api/chat")
def chat(request: PromptRequest):
    global excel_text_context
    print(f"🧐 Debug - Received Prompt: {request.prompt}")
    
    # 1. Reload Data (Safe to do here now that we removed 'async')
    load_data_global()

    try:
        # 2. Safety Check: Ensure context exists
        current_context = excel_text_context if excel_text_context else "The sheet is currently empty."
        
        # 3. Bind Tools
        tools = [add_task_tool, update_sheet_tool, send_email_tool]
        
        # 4. Initialize LLM
        # Suggestion: Ensure Config.openai_key is valid
        llm = ChatOpenAI(
            model="gpt-4o", 
            openai_api_key=Config.openai_key,
            temperature=0
        )
        llm_with_tools = llm.bind_tools(tools)

        # 5. System Prompt
        # Note: Double curly braces {{ }} are used here so Python doesn't break the f-string.
        system_msg = f"""
            You are an advanced Project Manager Agent connected to a live Google Sheet.
            CURRENT DATA IN SHEET:
            {current_context}
            RULES:
            1. **Truthfulness**: Answer questions ONLY based on the "CURRENT DATA IN SHEET".
            2. **Actions**: If the user wants to ADD, UPDATE, or EMAIL, you MUST call the appropriate tool.
            3. **Visuals**: If the user asks to *see* a chart or table, you must return a specific JSON object wrapped in markdown code blocks.
            ---
            ### VISUAL FORMATTING INSTRUCTIONS
            **1. FOR CHARTS**
            If the user wants a visualization, return this exact JSON structure:
            ```json
            {{
                "is_chart": true,
                "chart_type": "bar", 
                "title": "Chart Title Here",
                "data_source": "latest_sheet_data"
                }},
                "summary": "A short sentence explaining what this chart shows."
            }}
            ```
        """
      
        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content=request.prompt)
        ]

        print("🤖 AI Thinking...")
        ai_response = llm_with_tools.invoke(messages)
        
        # --- CASE A: TOOL CALLS ---
        if ai_response.tool_calls:
            print(f"🔧 AI decided to use {len(ai_response.tool_calls)} tools.")
            
            tool_map = {
                "add_task_tool": add_task_tool,
                "update_sheet_tool": update_sheet_tool,
                "send_email_tool": send_email_tool
            }
            
            results = []
            for tool_call in ai_response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                if tool_name in tool_map:
                    print(f"   -> Executing {tool_name}...")
                    try:
                        # Invoke the tool
                        tool_output = tool_map[tool_name].invoke(tool_args)
                        results.append(str(tool_output))
                    except Exception as tool_err:
                        error_msg = f"Tool {tool_name} failed: {str(tool_err)}"
                        print(f"❌ {error_msg}")
                        results.append(error_msg)
            
            return {
                "response": "Action Complete: " + " | ".join(results),
                "type": "text",
                "status": "success"
            }

        # --- CASE B: STANDARD CONVERSATION & VISUALS ---
        # IMPORTANT: Check if content is None (common if AI gets confused or errors out)
        if not ai_response.content:
            return {
                "response": "I processed the request but have no content to show. Please check the logs.", 
                "status": "success", 
                "type": "text"
            }

        content = ai_response.content.strip()
        
        # Check for JSON Visuals
        if "```json" in content:
            try:
                clean_json = content.split("```json")[1].split("```")[0].strip()
                data_obj = json.loads(clean_json)
                
                if data_obj.get("is_chart"):
                    return { "response": data_obj.get("summary"), "chart_data": data_obj, "type": "chart", "status": "success" }
                
                if data_obj.get("is_table"):
                     return { "response": data_obj.get("summary"), "table_data": data_obj, "type": "table", "status": "success" }
            except json.JSONDecodeError:
                print("⚠️ Failed to parse JSON from AI response.")
                # Fallback to returning the raw text if JSON fails
                pass 

        return {
            "response": content,
            "type": "text",
            "status": "success"
        }

    except Exception as e:
        print(f"❌ Chat Error: {e}")
        # Return the error to the frontend so you can see it in the UI
        return {"response": f"System Error: {str(e)}", "status": "error"}

# --- Entry Point ---
if __name__ == "__main__":
    # Railway assigns a PORT environment variable. 
    # If not found, it defaults to 8000 (for local testing).
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
