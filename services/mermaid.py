import os
import json
from datetime import datetime
from openai import OpenAI
from services.google_sheets_service import fetch_all_tasks
from typing import List, Optional
import sys

def generate_mermaid_gantt(tasks):
    # 1. Start the Gantt chart header
    # dateFormat should match how your dates are stored in Google Sheets (usually YYYY-MM-DD)
    gantt_lines = [
        "gantt",
        "    title Project Schedule",
        "    dateFormat  YYYY-MM-DD",
        "    axisFormat  %m-%d",
        "    section Project Tasks"
    ]

    for task in tasks:
        # Create a unique tag for this task (e.g., t1, t2)
        task_id = f"t{task.get('id')}"
        name = task.get("task_name", "Unnamed Task")
        
        # Ensure dates are strings. Provide a fallback if empty.
        start_date = str(task.get("start_date", "")).strip()
        end_date = str(task.get("end_date", "")).strip()
        
        # Get predecessor and format it as a tag (e.g., "1" becomes "t1")
        predecessor = str(task.get("predecessor", "")).strip()
        
        if predecessor and predecessor != "None" and predecessor != "":
            # Logic: Task Name : tag, after predecessor_tag, end_date
            pred_tag = f"t{predecessor}"
            line = f'    {name} : {task_id}, after {pred_tag}, {end_date}'
        else:
            # Logic: Task Name : tag, start_date, end_date
            line = f'    {name} : {task_id}, {start_date}, {end_date}'
        
        gantt_lines.append(line)

    return "\n".join(gantt_lines)

def generate_mermaid_flowchart(tasks):
    # Safety: If tasks is None or not a list, show an error node
    if not isinstance(tasks, list):
        return "graph TD\n    Error[Data format error: Expected list]"

    mermaid_lines = ["graph TD"]
    
    # 1. Create a safe ID -> Name mapping
    task_map = {}
    for task in tasks:
        # Check if 'task' is actually a dictionary
        if isinstance(task, dict):
            t_id = str(task.get("id", ""))
            t_name = task.get("task_name", "Unnamed Task")
            if t_id:
                task_map[t_id] = t_name

    # 2. Build the chart lines
    for task in tasks:
        # Skip anything that isn't a dictionary
        if not isinstance(task, dict):
            continue
            
        current_id = str(task.get("id", ""))
        current_name = task.get("task_name", "Unnamed Task")
        
        if not current_id:
            continue

        # Define node
        mermaid_lines.append(f'    {current_id}["{current_name}"]')

        # Handle Predecessor
        predecessor = str(task.get("predecessor", "")).strip()
        if predecessor and predecessor in task_map:
            mermaid_lines.append(f'    {predecessor} --> {current_id}')

    return "\n".join(mermaid_lines)


    return "\n".join(mermaid_lines)
