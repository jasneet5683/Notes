from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from config import API_TITLE, API_VERSION, HOST, PORT
from api.endpoints import router
from pydantic import BaseModel, Field
from typing import List, Optional
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="A smart project management chat agent powered by AI"
)

class ChatMessage(BaseModel):
    role: str
    content: str

class PromptRequest(BaseModel):
    prompt: str
    conversation_history: Optional[List[ChatMessage]] = None


# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (adjust for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request format", "errors": exc.errors()}
    )

# Include API router
app.include_router(router)

# Root endpoint
@app.get("/")
def root():
    return {
        "status": "online",
        "message": f"{API_TITLE} is running",
        "version": API_VERSION,
        "timestamp": datetime.now().isoformat(),
        "docs_url": "/docs"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    print(f"🚀 {API_TITLE} started successfully!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print(f"🛑 {API_TITLE} shut down gracefully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=True
    )
