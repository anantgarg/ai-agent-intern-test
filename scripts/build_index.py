from app.config import EMBEDDING_MODEL, INDEX_DIR, KNOWLEDGE_BASE
from app.retrieval.loader import load_documents
from app.retrieval.index import VectorIndex

docs=load_documents(KNOWLEDGE_BASE)
VectorIndex(EMBEDDING_MODEL, INDEX_DIR).build(docs)
print(f"Indexed {len(docs)} markdown sections into {INDEX_DIR}.")
