from apscheduler.schedulers.background import BackgroundScheduler
from app.modules.task_manager import fetch_all_tasks
import logging

def check_deadlines_and_notify():
    logging.info("Checking task deadlines...")
    tasks = fetch_all_tasks()
    # Add logic here to filter tasks near deadline and call email_service
    # Example: if task['due_date'] == today: send_email(...)
    pass

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_deadlines_and_notify, 'cron', hour=9, minute=0)
    scheduler.start()
    logging.info("Scheduler started.")
