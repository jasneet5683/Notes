import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    
    # Email Settings
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    SENDER_NAME = os.getenv("SENDER_NAME", "AI Assistant")
    
    # Google Sheets Settings
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS")  # Stored as a raw JSON string in Railway
    SHEET_NAME = "Task_Manager"  # Make sure this matches your Google Sheet Name exactly

    @staticmethod
    def get_google_sheet():
        """
        Connects to Google Sheets using credentials stored in the environment variable.
        Parses the JSON string directly.
        """
        if not Config.GOOGLE_CREDS_JSON:
            print("Error: GOOGLE_CREDS environment variable is missing.")
            return None

        try:
            # Parse the JSON string from the environment variable
            creds_dict = json.loads(Config.GOOGLE_CREDS_JSON)
            
            scope = [
                "https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client.open(SHEET_NAME).sheet1
            # Open the sheet by ID
            #return client.open_by_key(Config.GOOGLE_SHEET_ID).sheet1

        except json.JSONDecodeError:
            print("Error: The text in GOOGLE_CREDS is not valid JSON.")
            return None
        except Exception as e:
            print(f"Error connecting to Google Sheets: {e}")
            return None
