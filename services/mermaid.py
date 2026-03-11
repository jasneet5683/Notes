import os
import json
from datetime import datetime
from openai import OpenAI
from services.google_sheets_service import fetch_all_tasks
from typing import List, Optional
import sys

def generate_mermaid_gantt(tasks):
    # Neutral theme works very well for Gantt
    config = "%%{init: {'theme': 'neutral'}}%%"
    gantt_lines = [config, "gantt", "    title Project Schedule", ...]
    if not tasks:
        return "gantt\n    title No Data\n    section No Data\n    Empty :0, 1d"
    # 1. Configuration and Header
    gantt_lines = [
        "gantt",
        "    title Project Schedule",
        "    dateFormat  YYYY-MM-DD",  # Matches your '2026-03-02' format
        "    axisFormat  %m-%d",
        "    section Tasks"
    ]
    # 2. Build a set of existing IDs so we don't link to a non-existent task
    existing_ids = {str(t.get('task_id')) for t in tasks if t.get('task_id')}
    for task in tasks:
        t_id = str(task.get('task_id', ''))
        name = task.get('Task_Name', 'Unnamed Task')
        start = str(task.get('start_date', '')).strip()
        end = str(task.get('end_date', '')).strip()
        predecessor = str(task.get('predecessor', '')).strip()
        # Unique tag for this task (e.g., "t5")
        tag = f"t{t_id}"
        # 3. Check for relationship
        # Only use 'after' if the predecessor exists in our current task list
        if predecessor and predecessor != "0" and predecessor in existing_ids:
            # RELATIONSHIP: starts after the predecessor finishes
            # Syntax: Name : tag, after predecessor_tag, end_date
            line = f'    {name} : {tag}, after t{predecessor}, {end}'
        else:
            # NO RELATIONSHIP: starts on its specific start_date
            # Syntax: Name : tag, start_date, end_date
            line = f'    {name} : {tag}, {start}, {end}'
        
        gantt_lines.append(line)
    return "\n".join(gantt_lines)


def generate_mermaid_flowchart(tasks):
    config = "%%{init: {'theme': 'neutral', 'themeVariables': { 'primaryColor': '#007bff'}}}%%"
    mermaid_lines = [config, "graph TD"]
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
