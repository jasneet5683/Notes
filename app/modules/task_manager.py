import gspread
from oauth2client.service_account import ServiceAccountCredentials
from app.config import Config

# Setup Google Sheets Auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_sheet_client():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(Config.GOOGLE_CREDS_JSON, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(Config.GOOGLE_SHEET_ID).sheet1
        return sheet
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return None

def add_task_to_sheet(task_data: dict):
    sheet = get_sheet_client()
    if sheet:
        # Assuming dict keys match column order, e.g., Name, Client, DueDate
        row = list(task_data.values())
        sheet.append_row(row)
        return {"status": "success", "message": "Task added to sheet."}
    return {"status": "error", "message": "Database connection failed."}

def fetch_all_tasks():
    sheet = get_sheet_client()
    if sheet:
        return sheet.get_all_records()
    return []
