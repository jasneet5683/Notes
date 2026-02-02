from config import Config

def add_new_task(task_name, assigned_to, client_name, due_date):
    """
    Adds a new row to the connected Google Sheet.
    """
    sheet = Config.get_google_sheet()
    
    if not sheet:
        return {"status": "error", "message": "Database connection failed"}

    try:
        # Structure the row data
        new_row = [task_name, assigned_to, client_name, due_date]
        
        # Append to Google Sheet
        sheet.append_row(new_row)
        
        return {"status": "success", "message": f"Task '{task_name}' added."}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
