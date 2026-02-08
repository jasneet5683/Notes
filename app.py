from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import load_settings
from services.sheets_service import SheetsService
from services.task_service import TaskService
from services.ai_service import AIService
from services.speech_service import SpeechService
from models.schemas import Task, TaskCreate, TaskUpdate, ChatRequest, ChatResponse, SummarizeResponse


settings = load_settings()

app = FastAPI(title="Task_Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins if settings.cors_allow_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sheets = SheetsService(
    service_account_json=settings.google_service_account_json,
    sheet_name=settings.sheet_name,
)
tasks_service = TaskService(sheets)

ai_service = AIService(settings.openai_api_key) if settings.openai_api_key else None
speech_service = SpeechService(settings.openai_api_key) if settings.openai_api_key else None

# Serve frontend (optional). Works if you deploy a single service.
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/")
def root():
    return {"ok": True, "message": "Task_Manager API running. Frontend at /frontend"}


@app.get("/tasks", response_model=list[Task])
def list_tasks():
    return tasks_service.list_tasks()


@app.post("/tasks", response_model=Task)
def create_task(payload: TaskCreate):
    return tasks_service.create_task(payload)


@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: str, payload: TaskUpdate):
    updated = tasks_service.update_task(task_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not ai_service:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not configured")
    current_tasks = tasks_service.list_tasks()
    reply = ai_service.chat(req.message, current_tasks)
    return ChatResponse(reply=reply)


@app.get("/summarize", response_model=SummarizeResponse)
def summarize():
    if not ai_service:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not configured")
    current_tasks = tasks_service.list_tasks()
    summary = ai_service.summarize(current_tasks)
    return SummarizeResponse(summary=summary, count=len(current_tasks))


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not speech_service:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not configured")
    data = await file.read()
    text = speech_service.transcribe(data, filename=file.filename or "audio.wav")
    return {"text": text}
