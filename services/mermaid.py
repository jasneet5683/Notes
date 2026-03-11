import os
import json
from datetime import datetime
from openai import OpenAI
from services.google_sheets_service import fetch_all_tasks
from typing import List, Optional
import sys

def generate_mermaid_gantt() -> str:
    """Converts tasks into a Mermaid Gantt chart string"""
    tasks = fetch_all_tasks()  # Your existing function
    
    # Header for Mermaid Gantt
    mermaid_str = [
        "gantt",
        "    title Project Timeline",
        "    dateFormat  YYYY-MM-DD",
        "    axisFormat  %m-%d",
        "    section Project Tasks"
    ]

    for task in tasks:
        name = task.get("Task_Name", "Unnamed Task")
        start = task.get("start_date", "2024-01-01") # Ensure you have start_date
        end = task.get("end_date", "2024-01-10")
        priority = task.get("priority", "Medium")
        
        # Mapping priority to Mermaid tags (crit for High)
        tag = "crit, " if priority == "High" else ""
        
        # Format: Task Name :tag, start_date, end_date
        mermaid_str.append(f"    {name} :{tag}{start}, {end}")

    return "\n".join(mermaid_str)

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
