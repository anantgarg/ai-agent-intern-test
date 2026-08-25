"""Offline demo that exercises the same retrieval/tool/session pipeline without an API key."""
from app.config import *
from app.retrieval.index import VectorIndex
from app.retrieval.loader import load_documents
from app.retrieval.retriever import Retriever
from app.tools.order_lookup import OrderLookup
from app.memory.session import SessionStore
from app.observability.logger import JsonLogger
from app.agent import SupportAgent

idx=VectorIndex(EMBEDDING_MODEL,INDEX_DIR)
idx.build(load_documents(KNOWLEDGE_BASE))
agent=SupportAgent(Retriever(idx,8),OrderLookup(ORDERS_FILE),SessionStore(),OPENAI_MODEL,JsonLogger())

print('Aster & Row Support Agent — offline demo')
print('='*60)
for session, message in [
    ('demo-rag','What is the standard return window?'),
    ('demo-order','Where is ORD-1007 and when should it arrive?'),
    ('demo-multi','Do you ship internationally?'),
    ('demo-multi','What about Canada, and how long does it take?'),
    ('demo-safe','Can I put the entire Breeze Tumbler in the dishwasher?'),
]:
    result=agent.answer(session,message)
    print(f'\nUSER: {message}\nAGENT: {result["answer"]}')
    print('HANDOFF:',result['handoff'])
print('\nDemo complete.')
