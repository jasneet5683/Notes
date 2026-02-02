from config import Config
import pandas as pd

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
        
    except Exception as e:
        print(f"❌ Error processing data: {str(e)}")
        document_loaded = False
