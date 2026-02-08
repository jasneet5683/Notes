from typing import List, Optional
from models.schemas import Task, TaskCreate, TaskUpdate
from services.sheets_service import SheetsService
from utils.helpers import now_iso, new_id


class TaskService:
    def __init__(self, sheets: SheetsService):
        self.sheets = sheets

    def list_tasks(self) -> List[Task]:
        records = self.sheets.get_all()
        tasks: List[Task] = []
        for r in records:
            tasks.append(Task(**r))
        return tasks

    def create_task(self, payload: TaskCreate) -> Task:
        t = Task(
            id=new_id(),
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            due_date=payload.due_date,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        self.sheets.append([
            t.id, t.title, t.description or "", t.status, t.priority,
            t.due_date or "", t.created_at, t.updated_at
        ])
        return t

    def update_task(self, task_id: str, payload: TaskUpdate) -> Optional[Task]:
        row_idx = self.sheets.find_row_index_by_id(task_id)
        if not row_idx:
            return None

        # Get current row values (A..H)
        current = self.sheets.worksheet.row_values(row_idx)
        # Ensure length 8
        current = (current + [""] * 8)[:8]
        (
            _id, title, description, status, priority, due_date, created_at, updated_at
        ) = current

        title = payload.title if payload.title is not None else title
        description = payload.description if payload.description is not None else description
        status = payload.status if payload.status is not None else status
        priority = payload.priority if payload.priority is not None else priority
        due_date = payload.due_date if payload.due_date is not None else due_date
        updated_at = now_iso()

        updated = Task(
            id=_id,
            title=title,
            description=description or None,
            status=status,         # type: ignore
            priority=priority,     # type: ignore
            due_date=due_date or None,
            created_at=created_at,
            updated_at=updated_at,
        )

        self.sheets.update_row(row_idx, [
            updated.id,
            updated.title,
            updated.description or "",
            updated.status,
            updated.priority,
            updated.due_date or "",
            updated.created_at,
            updated.updated_at,
        ])
        return updated
