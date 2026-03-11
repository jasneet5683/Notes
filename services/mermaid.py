import os
import json
from datetime import datetime
from openai import OpenAI
from services.google_sheets_service import fetch_all_tasks
from typing import List, Optional
import sys

def get_task_meta(tasks):
    """Helper to create a set of valid IDs for validation"""
    return {str(t.get('task_id')) for t in tasks if t.get('task_id')}

# --- 1. FLOWCHART FUNCTION ---
def generate_mermaid_flowchart(tasks):
    if not tasks:
        return "graph TD\n    Empty[No tasks found]"

    valid_ids = get_task_meta(tasks)
    # Using 'neutral' theme for a clean look on white background
    mermaid_lines = ["%%{init: {'theme': 'neutral'}}%%", "graph TD"]
    
    for task in tasks:
        t_id = str(task.get("task_id", ""))
        t_name = task.get("Task_Name", "Unnamed Task")
        predecessor = str(task.get("predecessor", "")).strip()

        if not t_id:
            continue

        # Define the Node: t5["Task Name"]
        mermaid_lines.append(f'    t{t_id}["{t_name}"]')

        # Add Connection: t4 --> t5
        # We only draw the line if the predecessor ID actually exists in our data
        if predecessor and predecessor != "None" and predecessor in valid_ids:
            mermaid_lines.append(f'    t{predecessor} --> t{t_id}')

    return "\n".join(mermaid_lines)


# --- 2. GANTT CHART FUNCTION ---
def generate_mermaid_gantt(tasks):
    if not tasks:
        return "gantt\n    title No Data\n    section No Data\n    Empty :0, 1d"

    valid_ids = get_task_meta(tasks)
    gantt_lines = [
        "%%{init: {'theme': 'neutral'}}%%",
        "gantt",
        "    title Project Schedule",
        "    dateFormat  YYYY-MM-DD",
        "    axisFormat  %m-%d",
        "    section Tasks"
    ]

    for task in tasks:
        t_id = str(task.get('task_id', ''))
        name = task.get("Task_Name", "Unnamed Task")
        start = str(task.get("start_date", "")).strip()
        end = str(task.get("end_date", "")).strip()
        predecessor = str(task.get("predecessor", "")).strip()

        if not t_id:
            continue

        # Logic: If predecessor exists and is valid, use 'after'
        if predecessor and predecessor != "None" and predecessor in valid_ids:
            # RELATIONSHIP: starts after predecessor
            # Syntax: Name : t5, after t4, 2026-03-17
            line = f'    {name} : t{t_id}, after t{predecessor}, {end}'
        else:
            # NO RELATIONSHIP: starts on specific date
            # Syntax: Name : t5, 2026-03-02, 2026-03-17
            line = f'    {name} : t{t_id}, {start}, {end}'
        
        gantt_lines.append(line)

    return "\n".join(gantt_lines)
