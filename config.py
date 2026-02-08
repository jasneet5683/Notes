import os
from dotenv import load_dotenv

load_dotenv()

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "your-default-id")
SHEET_NAME = "Task_Manager"
CREDENTIALS_ENV_VAR = "GOOGLE_CREDENTIALS"


# API Configuration
API_TITLE = "Project Status Chat Agent"
API_VERSION = "1.0.0"
DEBUG_MODE = os.getenv("DEBUG", "False") == "True"
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
