import json
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEETS_CREDENTIALS, SPREADSHEET_ID
from models.schemas import TaskInput, TaskUpdate
from typing import List, Dict, Optional
#from datetime import datetime
from datetime import datetime, timedelta
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

#update task Status, end_date, assignment, predecessor

def update_task_field(task_name: str, field_type: str, new_value: str, request_analysis: str = None) -> dict:
    print(f"🤖 AI Analysis: {request_analysis}")
    try:
        worksheet = get_google_sheet()
        if not worksheet:
            return {"success": False, "message": "❌ Connection Error: Could not reach Google Sheets."}
        # 1. UPDATE THIS MAPPING TO MATCH YOUR EXACT SHEET HEADERS
        # Key = What AI sends (from enum)
        # Value = Exact Header Name in Google Sheet
        COLUMN_MAPPING = {
            "status": "status",           
            "priority": "Priority",       
            "assigned_to": "assigned_to", 
            "end_date": "end_date",       
            "predecessor": "predecessor"  
        }
        if field_type not in COLUMN_MAPPING:
            return {"success": False, "message": f"❌ Error: Field '{field_type}' is invalid."}
        target_header = COLUMN_MAPPING[field_type]
        # 2. Get Headers & Find Column Indices
        headers = worksheet.row_values(1)
        
        try:
            # Find the target column (e.g., 'status' or 'predecessor')
            target_col_index = headers.index(target_header) + 1
            
            # Find the Task Name column (Your sheet uses 'Task_Name')
            # We need this index to double-check, though mostly we use it for row lookup
            task_name_header = "Task_Name" 
            if task_name_header not in headers:
                 return {"success": False, "message": f"❌ Sheet Error: Header 'Task_Name' not found. Found: {headers}"}
            
        except ValueError:
            return {"success": False, "message": f"❌ Sheet Error: Column '{target_header}' not found in {headers}"}
        # 3. Find the Row by matching Task_Name
        all_records = worksheet.get_all_records()
        clean_target_name = task_name.strip().lower()
        
        row_to_update = -1
        for idx, record in enumerate(all_records):
            # Access the record using the exact header "Task_Name"
            current_task_name = str(record.get("Task_Name", "")).strip().lower()
            
            if current_task_name == clean_target_name:
                row_to_update = idx + 2 # +2 because sheet is 1-indexed and has header row
                break
        
        if row_to_update == -1:
            return {"success": False, "message": f"❌ Task '{task_name}' not found."}
        # 4. Update the specific cell
        worksheet.update_cell(row_to_update, target_col_index, new_value)
        return {
            "success": True, 
            "message": f"✅ Updated '{field_type}' to '{new_value}' for task '{task_name}'."
        }
    except Exception as e:
        print(f"Error updating sheet: {e}")
        return {"success": False, "message": f"❌ Technical error: {str(e)}"}

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
def get_task_statistics(group_by: str = "status", target_month: int = None, target_year: int = None, request_analysis: str = None) -> str:
    """
    Calculates statistics.
    group_by options: 'status', 'priority', 'assigned_to', 'month'.
    """
    tasks = fetch_all_tasks()
    
    # ### CHANGE 2: Return valid JSON string, not a Python string
    if not tasks:
        return json.dumps({}) 
    possible_formats = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]
    
    def parse_date(date_str):
        if not date_str: return None
        # Clean the string to remove accidental quotes
        date_str = str(date_str).strip().strip("'").strip('"') 
        for fmt in possible_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    filtered_tasks = []
    for task in tasks:
        raw_date = task.get("end_date", "") 
        dt_obj = parse_date(raw_date)
        
        # Logic fix: Allow filtering by Year OR Month+Year
        is_date_match = True
        if target_year:
            if not dt_obj or dt_obj.year != target_year:
                is_date_match = False
        if target_month:
            if not dt_obj or dt_obj.month != target_month:
                is_date_match = False
                
        if is_date_match:
            task['_dt_obj'] = dt_obj 
            filtered_tasks.append(task)
    values = []
    if group_by == "month":
        for task in filtered_tasks:
            dt = task.get('_dt_obj')
            if dt:
                values.append(dt.strftime("%b-%Y")) 
            else:
                values.append("No Date")
    else:
        key_map = {
            "status": "status",
            "priority": "Priority", # Ensure this matches your Sheet header exactly
            "assigned_to": "assigned_to"
        }
        # defaulting to "status" if key not found prevents errors
        target_key = key_map.get(group_by.lower(), "status")
        values = [str(task.get(target_key, "Unknown")) for task in filtered_tasks]
    counts = Counter(values)
    
    # ### CHANGE 3: Use json.dumps()
    # Python's str() uses single quotes {'a': 1}. 
    # JSON requires double quotes {"a": 1}. 
    # This helps the AI read the data correctly.
    return json.dumps(dict(counts))



def get_tasks_due_soon(all_tasks, days=15):
    """
    Filters a list of tasks to find those due within the next 'days'.
    
    Args:
        all_tasks (list): The list of dictionaries fetched from Google Sheets.
        days (int): The number of days to look ahead (default 15).
        
    Returns:
        str: A formatted string of tasks due soon, or a "No tasks" message.
    """
    # 1. Get the real Server Time
    today = datetime.now().date()
    cutoff_date = today + timedelta(days=days)

    print(f"DEBUG: Checking tasks between {today} and {cutoff_date}") # Check logs if issues persist

    upcoming_tasks = []

    for task in all_tasks:
        # Get the date string from the sheet (adjust key 'End_Date' to match your sheet header exactly)
        date_str = str(task.get("End_Date", "")).strip() 
        task_name = task.get("Task", "Unknown Task") # Adjust key 'Task' to match your sheet
        status = task.get("Status", "Pending")

        # Skip if empty or already done
        if not date_str or status.lower() == "completed":
            continue

        # 2. Robust Date Parsing
        # Google Sheets can send dates in many formats. We try the most common ones.
        task_date = None
        date_formats = [
            "%Y-%m-%d",  # 2024-02-25
            "%d-%m-%Y",  # 25-02-2024
            "%d/%m/%Y",  # 25/02/2024
            "%m/%d/%Y",  # 02/25/2024
            "%d-%b-%Y"   # 25-Feb-2024
        ]

        for fmt in date_formats:
            try:
                task_date = datetime.strptime(date_str, fmt).date()
                break # Found a match!
            except ValueError:
                continue # Try the next format
        
        # If we couldn't parse the date, skip this row (or log an error)
        if task_date is None:
            continue 

        # 3. The Math Comparison
        # Check if the task is in the future AND before the cutoff
        if today <= task_date <= cutoff_date:
            upcoming_tasks.append(f"- {task_name} (Due: {task_date}, Status: {status})")

    # 4. Final Output for the AI
    if not upcoming_tasks:
        return f"✅ No tasks due between {today} and {cutoff_date}."

    return f"📅 Found {len(upcoming_tasks)} tasks due in the next {days} days:\n" + "\n".join(upcoming_tasks)
