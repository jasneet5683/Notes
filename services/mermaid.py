import os
import json
from datetime import datetime
from openai import OpenAI
from services.google_sheets_service import fetch_all_tasks
from typing import List, Optional
import sys
import re

def parse_predecessors(pred_str):
    """
    Helper to turn '4, 5' or '4; 5' into ['4', '5'].
    Returns an empty list if no valid predecessors exist.
    """
    if not pred_str or str(pred_str).lower() == "none" or pred_str == 0:
        return []
    # Split by comma or semicolon and strip whitespace
    return [p.strip() for p in re.split(r'[;,]', str(pred_str)) if p.strip()]

def get_task_meta(tasks):
    return {str(t.get('task_id')) for t in tasks if t.get('task_id')}

# --- 1. FLOWCHART (Supports Multiple Arrows) ---
def generate_mermaid_flowchart(tasks):
    if not tasks:
        return "graph TD\n    Empty[No tasks found]"

    valid_ids = get_task_meta(tasks)
    mermaid_lines = ["%%{init: {'theme': 'neutral'}}%%", "graph TD"]
    
    for task in tasks:
        t_id = str(task.get("task_id", ""))
        t_name = task.get("Task_Name", "Unnamed Task")
        if not t_id: continue

        # Define the Node
        mermaid_lines.append(f'    t{t_id}["{t_name}"]')

        # Handle Multiple Predecessors
        preds = parse_predecessors(task.get("predecessor", ""))
        for p in preds:
            if p in valid_ids:
                # Add a separate line for every connection
                mermaid_lines.append(f'    t{p} --> t{t_id}')

    return "\n".join(mermaid_lines)


# --- 2. GANTT CHART (Supports Multiple Dependencies) ---
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
        if not t_id: continue

        preds = parse_predecessors(task.get("predecessor", ""))
        # Filter only predecessors that actually exist in our task list
        valid_preds = [f"t{p}" for p in preds if p in valid_ids]

        if valid_preds:
            # For Gantt, multiple 'after' IDs are separated by spaces
            # Syntax: Task Name : t5, after t3 t4, 2026-03-17
            pred_string = " ".join(valid_preds)
            line = f'    {name} : t{t_id}, after {pred_string}, {end}'
        else:
            line = f'    {name} : t{t_id}, {start}, {end}'
        
        gantt_lines.append(line)

    return "\n".join(gantt_lines)
