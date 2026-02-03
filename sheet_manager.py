from config import Config
import pandas as pd

#-------- Add task
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

#---- Load Data
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

#----- update_task

def internal_update_task(task_name, field, value):
    sheet = Config.get_google_sheet()
    if not sheet:
        return {"message": "Connection Error", "status": "error"}

    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # Flexible column matching
        col_map = {c.strip().lower().replace("_", " "): c for c in df.columns}
        
        task_col_actual = col_map.get("task name") or col_map.get("taskname") or col_map.get("task")
        if not task_col_actual:
            return {"message": "Could not find 'Task Name' column", "status": "error"}

        target_col_clean = field.strip().lower().replace("_", " ")
        target_col_actual = col_map.get(target_col_clean)
        if not target_col_actual:
            return {"message": f"Column '{field}' not found.", "status": "error"}

        mask = df[task_col_actual].astype(str).str.strip().str.lower() == task_name.strip().lower()
        if not mask.any():
            return {"message": f"Task '{task_name}' not found.", "status": "error"}

        df.loc[mask, target_col_actual] = value
        
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        load_data_global() # Refresh memory after update
        return {"message": f"✅ Updated '{task_name}': Set '{target_col_actual}' to '{value}'", "status": "success"}

    except Exception as e:
        return {"message": f"Error updating: {str(e)}", "status": "error"}
