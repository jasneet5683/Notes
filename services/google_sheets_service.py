import json
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEETS_CREDENTIALS, SPREADSHEET_ID
from models.schemas import TaskInput, TaskUpdate
from typing import List, Dict, Optional

# Initialize Google Sheets connection
def get_google_sheet():
    """
    Establishes connection to Google Sheets using credentials from environment.
    Returns the first worksheet of the Task_Manager spreadsheet.
    """
    try:
        # Retrieve credentials from environment
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")
        
        if not credentials_json:
            raise ValueError("GOOGLE_CREDENTIALS environment variable not set")
        
        # Parse credentials
        creds_dict = json.loads(credentials_json)
        
        # Define scopes for Google Sheets and Drive access
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Authorize and connect
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
        client = gspread.authorize(creds)
        
        # Open spreadsheet by name
        spreadsheet = client.open("Task_Manager")
        return spreadsheet.sheet1
        
    except ValueError as ve:
        print(f"❌ Configuration Error: {ve}")
        return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
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
            task.start_date,
            task.end_date,
            task.status,
            task.assigned_to,
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
