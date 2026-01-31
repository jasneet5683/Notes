from fastapi import FastAPI, UploadFile, File, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.modules.task_manager import add_task_to_sheet
from app.modules.transcript_service import transcribe_audio_and_summarize
from app.modules.scheduler import start_scheduler
from app.modules.email_service import send_task_creation_email

app = FastAPI()

# Setup Templates for HTML Frontend
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.get("/")
def read_root(request: Request):
    # Renders your HTML frontend
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/create-task")
async def create_task(task: dict):
    # 1. Add to Google Sheet
    db_result = add_task_to_sheet(task)
    
    # 2. Send Email Notification
    if db_result['status'] == 'success':
        send_task_creation_email(
            task.get('email'), 
            task.get('task_name'), 
            task.get('client'), 
            task.get('due_date')
        )
    return db_result

@app.post("/api/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    contents = await file.read()
    result = transcribe_audio_and_summarize(contents)
    return result
