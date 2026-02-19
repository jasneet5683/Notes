import json
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEETS_CREDENTIALS, SPREADSHEET_ID
from models.schemas import TaskInput, TaskUpdate
from typing import List, Dict, Optional
from datetime import datetime
from collections import Counter

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

def add_task_to_sheet(task: TaskInput, successor: str = "") -> Dict:
    """
    Add a new task to Google Sheets with auto-incremented task_id.
    
    New Row Structure:
    [task_id, task_name, start_date, end_date, status, assigned_to, client, priority, successor]
    """
    try:
        worksheet = get_google_sheet()
        if not worksheet:
            return {"success": False, "error": "Could not connect to Google Sheets"}
        
        # 1. Fetch all existing records to calculate the next ID
        all_records = worksheet.get_all_records()
        
        # 2. Calculate Next ID
        if not all_records:
            next_id = 1
        else:
            existing_ids = []
            for record in all_records:
                # Safely extract IDs (handling potential strings/empty cells)
                try:
                    # Assumes task_id is the first column (key: 'task_id')
                    # Adjust key string if your header is different, e.g., 'ID'
                    tid = record.get("task_id", 0) 
                    if str(tid).isdigit():
                        existing_ids.append(int(tid))
                except (ValueError, TypeError):
                    continue
            
            next_id = (max(existing_ids) + 1) if existing_ids else 1
        
        # 3. Build the new row
        # Order: ID | Name | Start | End | Status | Assigned | Client | Priority | Successor
        new_row = [
            next_id,
            task.task_name,
            task.start_date,
            task.end_date,
            task.status,
            task.assigned_to,
            task.client,
            task.priority,
            task.predecessor  # New field
        ]
        
        worksheet.append_row(new_row)
        
        return {
            "success": True, 
            "task_id": next_id, 
            "message": f"Task '{task.task_name}' added with ID: {next_id}"
        }
    except Exception as e:
        print(f"❌ Error adding task: {e}")
        return {"success": False, "error": str(e)}

def find_task_id_by_name(partial_name: str) -> str:
    """
    Searches for a task by name and returns its Task ID.
    Returns empty string if not found.
    """
    try:
        tasks = fetch_all_tasks() # Re-use your existing fetch function
        if not tasks:
            return ""

        partial_name = partial_name.lower().strip()
        
        for task in tasks:
            # Adjust key based on your sheet headers
            current_name = str(task.get("Task_Name", "")).lower().strip()
            
            # Simple substring match
            if partial_name in current_name:
                return str(task.get("task_id", ""))
                
        return ""
    except Exception as e:
        print(f"Error finding task ID: {e}")
        return ""

#----- New AI Wrapper function
def add_task_from_ai(task_name: str, assigned_to: str = "Unassigned", priority: str = "Medium", 
                     end_date: str = "", client: str = "Unknown", predecessor_name: str = "") -> str:
    """
    Smart Wrapper: 
    1. Resolves predecessor name to ID.
    2. Auto-calculates start_date based on predecessor's end_date (if applicable).
    """
    try:
        # Defaults
        calculated_start_date = datetime.now().strftime("%Y-%m-%d")
        predecessor_id = ""

        # --- SMART LOGIC: Handle Predecessor ---
        if predecessor_name:
            # 1. Find the ID
            found_id = find_task_id_by_name(predecessor_name)
            
            if found_id:
                predecessor_id = found_id
                
                # 2. Smart Scheduling: Fetch the predecessor task to get its End Date
                all_tasks = fetch_all_tasks()
                parent_task = next((t for t in all_tasks if str(t.get("task_id")) == found_id), None)
                
                if parent_task:
                    parent_end = parent_task.get("end_date", "")
                    if parent_end:
                        # Logic: Start the new task 1 day AFTER the predecessor ends
                        try:
                            p_date = datetime.strptime(parent_end, "%Y-%m-%d")
                            new_start = p_date + timedelta(days=1)
                            calculated_start_date = new_start.strftime("%Y-%m-%d")
                        except ValueError:
                            pass # Keep default if date parsing fails
            else:
                return f"⚠️ I couldn't find a task named '{predecessor_name}' to set as a predecessor. Task NOT added."

        # --- Create Input Object ---
        new_task_input = TaskInput(
            task_name=task_name,
            start_date=calculated_start_date, # Uses smart date or today
            end_date=end_date,
            status="Pending",
            assigned_to=assigned_to,
            client=client, 
            priority=priority,
            predecessor=predecessor_id  # We send the ID, not the name, to the sheet
        )
        
        # Call the main sheet function
        result = add_task_to_sheet(new_task_input)
        
        if result["success"]:
            msg = f"✅ Added '{task_name}' (ID: {result['id']})"
            if predecessor_id:
                msg += f" linked to predecessor ID {predecessor_id}."
            return msg
        else:
            return f"❌ Failed: {result.get('error')}"

    except Exception as e:
        return f"❌ Error: {str(e)}"

def check_schedule_conflicts() -> str:
    """
    Scans all tasks to ensure that if Task B depends on Task A,
    Task B starts AFTER Task A ends.
    """
    tasks = fetch_all_tasks()
    if not tasks:
        return "No tasks to analyze."

    # 1. Build a lookup map for speed { "task_id": task_object }
    task_map = {str(t.get("task_id")): t for t in tasks}
    conflicts = []

    for task in tasks:
        # Get this task's predecessor ID
        pred_id = str(task.get("predecessor", "")).strip()
        
        # If it has a predecessor AND the predecessor exists in our map
        if pred_id and pred_id in task_map:
            parent = task_map[pred_id]
            
            # Get Dates
            parent_end = parent.get("end_date", "")
            child_start = task.get("start_date", "")
            
            if parent_end and child_start:
                try:
                    p_end_dt = datetime.strptime(parent_end, "%Y-%m-%d")
                    c_start_dt = datetime.strptime(child_start, "%Y-%m-%d")
                    
                    # LOGIC: Conflict if Child starts BEFORE Parent ends
                    if c_start_dt < p_end_dt:
                        conflicts.append(
                            f"⚠️ CONFLICT: Task '{task['Task_Name']}' starts on {child_start}, "
                            f"but its predecessor '{parent['Task_Name']}' doesn't end until {parent_end}."
                        )
                except ValueError:
                    continue # Skip invalid dates

    if not conflicts:
        return "✅ Schedule is healthy! No dependency conflicts found."
    
    return "❌ Schedule Conflicts Found:\n" + "\n".join(conflicts)


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
                # 3. Update Column 5 (Status)
                # Based on your order: Task(2), Start(3), End(4), Status(5)
                worksheet.update_cell(idx, 5, update.new_status) 
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
    tasks = fetch_all_tasks()
    if not tasks:
        return "No tasks found in database."
    filtered_results = []
    
    # Standard formats
    possible_formats = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]
    print(f"DEBUG: Filtering started. Target: M={target_month}, Y={target_year}")
    for task in tasks:
        # 1. Get the date string using the CORRECT column key: 'end_date'
        # We use .get('end_date') directly based on your logs
        raw_date_str = str(task.get("end_date", "")).strip().strip("'")
        
        if not raw_date_str:
            continue
        parsed_date = None
        # 2. Try to parse
        for fmt in possible_formats:
            try:
                parsed_date = datetime.strptime(raw_date_str, fmt)
                break 
            except ValueError:
                continue 
        
        if not parsed_date:
            print(f"DEBUG: Could not parse date: '{raw_date_str}'")
            continue
        # 3. Check Match
        match = True
        
        if target_date:
            normalized_date_str = parsed_date.strftime("%Y-%m-%d")
            if normalized_date_str != target_date:
                match = False
        
        if target_month and target_year:
            if parsed_date.month != target_month or parsed_date.year != target_year:
                match = False
        if match:
            # We also update these keys to match your logs: 'Task_Name', 'status', 'Priority'
            task_name = task.get("Task_Name", "Unknown")
            status = task.get("status", "Unknown")
            priority = task.get("Priority", "Unknown")
            
            print(f"DEBUG: Match found! {task_name}")
            filtered_results.append(f"- {task_name} (Due: {raw_date_str}, Status: {status}, Priority: {priority})")
    if not filtered_results:
        return "No tasks found matching that date criteria."
    return "Here are the matching tasks:\n" + "\n".join(filtered_results)

#--- Function for Stats
def get_task_statistics(group_by: str = "status", target_month: int = None, target_year: int = None) -> str:
    """
    Calculates statistics.
    group_by options: 'status', 'priority', 'assigned_to', 'month'.
    target_month/year: Optional filters (e.g., "Get status counts for March only").
    """
    tasks = fetch_all_tasks()
    if not tasks:
        return "{}"
    # 1. Define Date Parsing Helper (Same robust logic as before)
    possible_formats = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]
    
    def parse_date(date_str):
        if not date_str: return None
        date_str = str(date_str).strip().strip("'")
        for fmt in possible_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    # 2. Filter List (if Month/Year provided)
    filtered_tasks = []
    for task in tasks:
        # Get raw date string from 'end_date' key
        raw_date = task.get("end_date", "") 
        dt_obj = parse_date(raw_date)
        
        # If filtering is requested, check the date
        if target_month and target_year:
            if not dt_obj: continue # Skip invalid dates if filtering
            if dt_obj.month != target_month or dt_obj.year != target_year:
                continue
        
        # Add a helper 'parsed_date_obj' to the task dict for the next step
        task['_dt_obj'] = dt_obj 
        filtered_tasks.append(task)
    # 3. Grouping Logic
    values = []
    
    if group_by == "month":
        # Strategy: Extract "MMM-YYYY" from every task
        for task in filtered_tasks:
            dt = task.get('_dt_obj')
            if dt:
                values.append(dt.strftime("%b-%Y")) # e.g., "Mar-2026"
            else:
                values.append("No Date")
                
    else:
        # Standard columns: Status, Priority, Assigned To
        key_map = {
            "status": "status",
            "priority": "Priority",
            "assigned_to": "assigned_to"
        }
        target_key = key_map.get(group_by.lower(), "status")
        values = [str(task.get(target_key, "Unknown")) for task in filtered_tasks]
    # 4. Count and Return
    counts = Counter(values)
    return str(dict(counts))

