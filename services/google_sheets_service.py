import json
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEETS_CREDENTIALS, SPREADSHEET_ID
from models.schemas import TaskInput, TaskUpdate
from typing import List, Dict, Optional
from datetime import datetime

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

#----- New AI Wrapper function
def add_task_from_ai(task_name: str, assigned_to: str = "Unassigned", priority: str = "Medium", end_date: str = "", client: str = "Unknown") -> str:
    """
    Wrapper for AI to add tasks. 
    Converts string arguments into a TaskInput object and calls the main function.
    """
    try:
        # 1. Set Defaults
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # 2. Create the TaskInput object (This matches your Pydantic model)
        # Note: We default 'client' to 'General' and 'status' to 'Pending'
        new_task_input = TaskInput(
            task_name=task_name,
            start_date=current_date,
            end_date=end_date,
            status="Pending",
            assigned_to=assigned_to,
            client=client, 
            priority=priority
        )
        # 3. Call your EXISTING function
        success = add_task_to_sheet(new_task_input)
        if success:
            return f"✅ Successfully added task '{task_name}'."
        else:
            return "❌ Failed to add task. Please check the logs."
    except Exception as e:
        return f"❌ Error: {str(e)}"


def update_task_status(update: TaskUpdate) -> bool:
    """Update the status of an existing task"""
    try:
        worksheet = get_google_sheet()
        if not worksheet:
            return False
        
        all_records = worksheet.get_all_records()
        
        # 1. Clean the incoming name (Remove leading/trailing spaces & lower case)
        target_name_clean = update.task_name.strip().lower()
        
        # Find and update the task
        for idx, record in enumerate(all_records, start=2):  # Start from row 2 (after header)
            
            # 2. Get the name using the correct key (likely 'Task_Name') 
            # and clean it (strip spaces)
            sheet_task_name = str(record.get("Task_Name", record.get("Task Name", ""))).strip().lower()
            
            if sheet_task_name == target_name_clean:
                # 3. Update Column 4 (Status)
                # Based on your order: Task(1), Start(2), End(3), Status(4)
                worksheet.update_cell(idx, 4, update.new_status) 
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
# services/google_sheets_service.py

def update_task_field(task_name: str, field_type: str, new_value: str) -> str:
    """
    Updates a specific field for a task in Google Sheets.
    field_type options: 'status', 'priority', 'assigned_to', 'end_date'
    """
    try:
        worksheet = get_google_sheet()
        if not worksheet:
            return "Error: Could not connect to Google Sheets."

        all_records = worksheet.get_all_records()
        
        # 1. Map the AI's "field_type" to your actual Google Sheet Header Names and Column Index
        # IMPORTANT: Check your sheet. If 'Status' is Column D (4), put 4. 
        # If 'Priority' is Column F (6), put 6. Adjust these numbers!
        COLUMN_MAPPING = {
            "status": {"col": 4, "header": "status"},
            "assigned_to": {"col": 5, "header": "assigned_to"},
            "priority": {"col": 7, "header": "Priority"}, 
            "end_date": {"col": 3, "header": "end_date"}
        }

        if field_type not in COLUMN_MAPPING:
            return f"Error: I don't know how to update the field '{field_type}'."

        target_col_index = COLUMN_MAPPING[field_type]["col"]

        # 2. Find the Row
        task_name_clean = task_name.strip().lower()
        
        for idx, record in enumerate(all_records, start=2): # Start at 2 for headers
            current_task = str(record.get("Task_Name", record.get("Task Name", ""))).strip().lower()
            
            if current_task == task_name_clean:
                # 3. Update the specific cell
                worksheet.update_cell(idx, target_col_index, new_value)
                return f"Successfully updated '{field_type}' to '{new_value}' for task '{task_name}'."

        return f"Task '{task_name}' not found."

    except Exception as e:
        print(f"Error updating sheet: {e}")
        return f"Technical error while updating: {str(e)}"

# Filter tasks by Date

def filter_tasks_by_date(target_month: int = None, target_year: int = None, target_date: str = None) -> str:
    """
    Filters tasks based on a specific date, or a month/year combination.
    """
    tasks = fetch_all_tasks()
    if not tasks:
        return "No tasks found in database."

    filtered_results = []
    
    for task in tasks:
        # Assuming date format in Sheet is YYYY-MM-DD
        end_date_str = str(task.get("End Date", "")).strip()
        
        try:
            # Parse the date from the sheet
            task_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            
            match = True
            
            # Filter by exact date
            if target_date:
                if end_date_str != target_date:
                    match = False
            
            # Filter by Month and Year
            if target_month and target_year:
                if task_date.month != target_month or task_date.year != target_year:
                    match = False

            if match:
                filtered_results.append(f"- {task.get('Task Name')} (Due: {end_date_str}, Status: {task.get('Status')})")

        except ValueError:
            # Skip rows where date is missing or invalid format
            continue

    if not filtered_results:
        return "No tasks found matching that date criteria."

    return "Here are the matching tasks:\n" + "\n".join(filtered_results)

