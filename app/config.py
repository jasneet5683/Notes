import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class Config:
    # Basic API Keys and Config
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
    # This variable will hold the raw JSON string from Railway
    GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS")

    @staticmethod
    def get_google_sheet():
        """
        Connects to Google Sheets using credentials stored in the environment variable.
        """
        if not Config.GOOGLE_CREDS_JSON:
            print("Error: GOOGLE_CREDS environment variable is missing.")
            return None

        try:
            # 1. Parse the raw JSON string into a Python dictionary
            creds_dict = json.loads(Config.GOOGLE_CREDS_JSON)
            
            # 2. Define the scope
            scope = [
                "https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"
            ]
            
            # 3. Authenticate using the dictionary
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            
            # 4. Open the sheet
            return client.open_by_key(Config.GOOGLE_SHEET_ID).sheet1
            
        except json.JSONDecodeError:
            print("Error: The text in GOOGLE_CREDS is not valid JSON.")
            return None
        except Exception as e:
            print(f"Error connecting to Google Sheets: {e}")
            return None
