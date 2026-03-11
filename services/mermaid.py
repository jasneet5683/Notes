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
    # 1. Start the Mermaid string
    mermaid_lines = ["graph TD"]
    
    # 2. Create a lookup dictionary for ID -> Task Name
    # We cast to string to avoid the 'int' object error we saw earlier
    task_map = {str(task.get("id")): task.get("task_name", "Unnamed Task") for task in tasks}

    for task in tasks:
        current_id = str(task.get("id"))
        current_name = task.get("task_name", "Unnamed Task")
        
        # 3. Define the current node with a label: ID["Name"]
        # This ensures the box shows the text, not the number
        mermaid_lines.append(f'    {current_id}["{current_name}"]')

        # 4. Handle Predecessors
        predecessor_raw = task.get("predecessor")
        
        if predecessor_raw:
            # Split if there are multiple predecessors (e.g., "1, 2")
            preds = str(predecessor_raw).split(',')
            
            for p in preds:
                p_id = p.strip()
                # Only draw the line if the predecessor actually exists in our data
                if p_id in task_map:
                    mermaid_lines.append(f'    {p_id} --> {current_id}')

    return "\n".join(mermaid_lines)
