from typing import List
from openai import OpenAI
from models.schemas import Task


class AIService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def chat(self, message: str, tasks: List[Task]) -> str:
        task_lines = "\n".join(
            [f"- [{t.status}] ({t.priority}) {t.title} (due: {t.due_date or 'n/a'}) id={t.id}" for t in tasks]
        )

        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful task manager assistant."},
                {"role": "user", "content": f"Current tasks:\n{task_lines}\n\nUser message: {message}"},
            ],
        )
        return resp.choices[0].message.content or ""

    def summarize(self, tasks: List[Task]) -> str:
        task_lines = "\n".join(
            [f"- [{t.status}] ({t.priority}) {t.title} due:{t.due_date or 'n/a'}" for t in tasks]
        )
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarize tasks into a short actionable status update."},
                {"role": "user", "content": task_lines},
            ],
        )
        return resp.choices[0].message.content or ""
