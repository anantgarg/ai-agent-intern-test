from fastapi import FastAPI
from pydantic import BaseModel
from .config import *
from .retrieval.index import VectorIndex
from .retrieval.loader import load_documents
from .retrieval.retriever import Retriever
from .tools.order_lookup import OrderLookup
from .memory.session import SessionStore
from .observability.logger import JsonLogger
from .agent import SupportAgent

app = FastAPI(title="Aster & Row Reliable Support Agent", version="1.0.0")
index = VectorIndex(EMBEDDING_MODEL, INDEX_DIR)
try:
    index.load()
except Exception:
    index.build(load_documents(KNOWLEDGE_BASE))
retriever = Retriever(index, TOP_K)
orders = OrderLookup(ORDERS_FILE)
sessions = SessionStore()
logger = JsonLogger()
agent = SupportAgent(retriever, orders, sessions, OPENAI_MODEL, logger)

class ChatRequest(BaseModel):
    session_id: str = "demo"
    message: str

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/chat")
def chat(request: ChatRequest):
    return agent.answer(request.session_id, request.message)
