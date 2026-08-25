import os
import frontmatter
import chromadb
from chromadb.config import Settings

KB_DIR = os.path.join(os.path.dirname(__file__), 'knowledge-base')

def load_documents():
    docs = []
    for filename in os.listdir(KB_DIR):
        if not filename.endswith('.md'):
            continue
        filepath = os.path.join(KB_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            
            # Simple chunking by header '## '
            content = post.content
            chunks = content.split('\n## ')
            
            # Re-add '## ' to all chunks except the first one (which might be the title/top level)
            for i, chunk in enumerate(chunks):
                if i > 0:
                    chunk = '## ' + chunk
                if chunk.strip():
                    docs.append({
                        "id": f"{filename}-chunk-{i}",
                        "content": chunk.strip(),
                        "metadata": {
                            "filename": filename,
                            "title": post.get("title", ""),
                            "status": post.get("status", ""),
                            "audience": post.get("audience", ""),
                            "document_id": post.get("document_id", "")
                        }
                    })
    return docs

class RAGSystem:
    def __init__(self):
        # In-memory Chroma client for simplicity
        self.chroma_client = chromadb.Client(Settings(is_persistent=False))
        # Default embedding model is all-MiniLM-L6-v2 which runs locally
        self.collection = self.chroma_client.get_or_create_collection(name="knowledge_base")
        self._initialize_db()

    def _initialize_db(self):
        docs = load_documents()
        if not docs:
            return
            
        ids = [doc["id"] for doc in docs]
        documents = [doc["content"] for doc in docs]
        metadatas = [doc["metadata"] for doc in docs]
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        retrieved_chunks = []
        for i in range(len(results["ids"][0])):
            retrieved_chunks.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results["distances"] else None
            })
            
        return retrieved_chunks

    def format_retrieved_context(self, chunks: list[dict]) -> str:
        if not chunks:
            return "No relevant documents found."
            
        context_parts = []
        for chunk in chunks:
            meta = chunk["metadata"]
            header = f"--- Document: {meta['filename']} (Status: {meta['status']}) ---"
            context_parts.append(f"{header}\n{chunk['content']}\n")
            
        return "\n".join(context_parts)
