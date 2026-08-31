# app/api.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.main import answer


app = FastAPI(title="AI Support Agent")


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST / RESPONSE MODELS
# =========================================================

class ChatRequest(BaseModel):
    message: str
    history: list = []


class ChatResponse(BaseModel):
    answer: str
    sources: list
    handoff: bool
    tool: str


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "AI Support Agent is running"
    }


# =========================================================
# CHAT
# =========================================================

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    result = answer(
        request.message,
        request.history
    )

    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "handoff": result.get("handoff", False),
        "tool": result.get("tool", "not_called"),
    }