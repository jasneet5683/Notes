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
    return {
        "document_loaded": document_loaded,
        "data_preview": excel_text_context[:100] if excel_text_context else "No data loaded"
    }
@tool
def update_sheet_tool(task_name: str, field: str, value: str):
    """
    Updates a task in the Google Sheet. 
    Use this tool when the user asks to modify, update, change, or set a value in the tracker.
    """
    print(f"🛠 Tool Triggered: Updating {task_name}...")
    result = internal_update_task(task_name, field, value)
    return result["message"]

# --- Entry Point ---
if __name__ == "__main__":
    # Railway assigns a PORT environment variable. 
    # If not found, it defaults to 8000 (for local testing).
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
