import os
import json
from datetime import datetime
from openai import OpenAI
from services.google_sheets_service import fetch_all_tasks
from typing import List, Optional
import sys

def generate_mermaid_gantt(tasks):
    if not tasks:
        return "gantt\n    title No Data\n    section No Data\n    Empty :0, 1d"

    gantt_lines = [
        "gantt",
        "    title Project Schedule",
        "    dateFormat  YYYY-MM-DD",
        "    axisFormat  %m-%d",
        "    section Tasks"
    ]

    for task in tasks:
        t_id = f"t{task.get('task_id')}"
        name = task.get("Task_Name", "Unnamed Task")
        start = str(task.get("start_date", "")).strip()
        end = str(task.get("end_date", "")).strip()
        predecessor = str(task.get("predecessor", "")).strip()

        if predecessor and predecessor != "None" and predecessor != "":
            # Format: Task Name : tag, after t_predecessor, end_date
            line = f'    {name} : {t_id}, after t{predecessor}, {end}'
        else:
            # Format: Task Name : tag, start_date, end_date
            line = f'    {name} : {t_id}, {start}, {end}'
        
        gantt_lines.append(line)

    return "\n".join(gantt_lines)

def generate_mermaid_flowchart(tasks):
    if not tasks:
        return "graph TD\n    Empty[No tasks found]"

    mermaid_lines = ["graph TD"]
    
    # 1. Map task_id to Task_Name (matching your log keys)
    task_map = {}
    for task in tasks:
        t_id = str(task.get("task_id", ""))
        t_name = task.get("Task_Name", "Unnamed Task")
        if t_id:
            task_map[t_id] = t_name

    # 2. Create the nodes and connections
    for task in tasks:
        current_id = str(task.get("task_id", ""))
        current_name = task.get("Task_Name", "Unnamed Task")
        
        if not current_id:
            continue

        # Add the node: e.g., 5["Raise CCF for Notification"]
        mermaid_lines.append(f'    {current_id}["{current_name}"]')

        # Add the connection if predecessor exists
        predecessor = str(task.get("predecessor", "")).strip()
        
        # Check if predecessor is a valid ID in our map
        if predecessor and predecessor != "None" and predecessor in task_map:
            mermaid_lines.append(f'    {predecessor} --> {current_id}')

    return "\n".join(mermaid_lines)
