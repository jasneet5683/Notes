import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEETS_CREDENTIALS, SPREADSHEET_ID
from models.schemas import TaskInput, TaskUpdate
from typing import List, Dict, Optional

# Initialize Google Sheets connection
def get_google_sheet():
    """Authenticate and return Google Sheets connection"""
    try:
        creds_json = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(SPREADSHEET_ID)
        return sheet.worksheet(0)  # Access first worksheet
    except Exception as e:
        print(f"❌ Google Sheets connection error: {e}")
        return None

def fetch_all_tasks() -> List[Dict]:
    """Retrieve all tasks from Google Sheets"""
    try:
        worksheet = get_google_sheet()
        if not worksheet:
            return []
        
        all_records = worksheet.get_all_records()
        return all_records if all_records else []
    except Exception as e:
        print(f"❌ Error fetching tasks: {e}")
        return []

def add_task_to_sheet(task: TaskInput) -> bool:
    """Add a new task to Google Sheets"""
    try:
        worksheet = get_google_sheet()
        if not worksheet:
            return False
        
        new_row = [
            task.task_name,
            task.assigned_to,
            task.start_date,
            task.end_date,
            task.status,
            task.client,
            task.priority
        ]
        worksheet.append_row(new_row)
        return True
    except Exception as e:
        print(f"❌ Error adding task: {e}")
        return False

def update_task_status(update: TaskUpdate) -> bool:
    """Update the status of an existing task"""
    try:
        worksheet = get_google_sheet()
        if not worksheet:
            return False
        
        all_records = worksheet.get_all_records()
        
        # Find and update the task
        for idx, record in enumerate(all_records, start=2):  # Start from row 2 (after header)
            if record.get("Task Name", "").lower() == update.task_name.lower():
                worksheet.update_cell(idx, 5, update.new_status)  # Column E (Status)
                return True
        
        return False
    except Exception as e:
        print(f"❌ Error updating task: {e}")
        return False

def search_tasks(search_term: str) -> List[Dict]:
    """Search tasks by name or assigned person"""
    try:
        tasks = fetch_all_tasks()
        return [
            task for task in tasks 
            if search_term.lower() in str(task).lower()
        ]
    except Exception as e:
        print(f"❌ Error searching tasks: {e}")
        return []
