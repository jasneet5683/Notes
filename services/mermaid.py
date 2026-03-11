import os
import json
from datetime import datetime
from openai import OpenAI
from services.google_sheets_service import (
    fetch_all_tasks, 
    update_task_field, 
    add_task_from_ai,
    filter_tasks_by_date,
    get_task_statistics,
    check_schedule_conflicts,
    get_tasks_due_soon
)
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

def generate_mermaid_flowchart() -> str:
    """Converts tasks and predecessors into a Mermaid Flowchart string"""
    tasks = fetch_all_tasks()
    
    mermaid_str = ["graph TD"]
    
    for task in tasks:
        name = task.get("Task_Name", "Task").replace(" ", "_")
        predecessor = task.get("predecessor", "").replace(" ", "_")
        
        # If there is a dependency, draw an arrow
        if predecessor and predecessor.lower() != "none":
            mermaid_str.append(f"    {predecessor} --> {name}")
        else:
            # Just define the node if no predecessor
            mermaid_str.append(f"    {name}")

    return "\n".join(mermaid_str)
