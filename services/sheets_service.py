from typing import Any, Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials


class SheetsService:
    def __init__(self, service_account_json: dict, sheet_name: str, worksheet_name: str = "Tasks"):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(service_account_json, scopes=scopes)
        self.client = gspread.authorize(creds)

        self.sheet = self.client.open(sheet_name)
        self.worksheet = self._get_or_create_worksheet(worksheet_name)

        self._ensure_header()

    def _get_or_create_worksheet(self, name: str):
        try:
            return self.sheet.worksheet(name)
        except gspread.WorksheetNotFound:
            return self.sheet.add_worksheet(title=name, rows=1000, cols=20)

    def _ensure_header(self) -> None:
        header = [
            "id", "title", "description", "status", "priority",
            "due_date", "created_at", "updated_at"
        ]
        first_row = self.worksheet.row_values(1)
        if first_row != header:
            self.worksheet.clear()
            self.worksheet.append_row(header)

    def get_all(self) -> List[Dict[str, Any]]:
        return self.worksheet.get_all_records()

    def append(self, row: List[Any]) -> None:
        self.worksheet.append_row(row)

    def find_row_index_by_id(self, task_id: str) -> Optional[int]:
        # IDs are in column 1, header is row 1
        col = self.worksheet.col_values(1)
        for idx, val in enumerate(col, start=1):
            if idx == 1:
                continue
            if val == task_id:
                return idx
        return None

    def update_row(self, row_index: int, row: List[Any]) -> None:
        # Update full row, starting col 1
        self.worksheet.update(f"A{row_index}:H{row_index}", [row])
