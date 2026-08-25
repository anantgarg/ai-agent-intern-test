import json
from pathlib import Path
from .loader import Document

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import faiss
    EMBEDDINGS_AVAILABLE = True
except Exception:
    EMBEDDINGS_AVAILABLE = False
    np = None

class VectorIndex:
    """FAISS + Sentence Transformers index with a small TF-IDF fallback for offline tests."""
    def __init__(self, model_name: str, index_dir: Path):
        self.model_name=model_name
        self.index_dir=Path(index_dir)
        self.index_dir.mkdir(parents=True,exist_ok=True)
        self.documents=[]
        self.index=None
        self.model=None
        self.vectorizer=None
        self.matrix=None
        if EMBEDDINGS_AVAILABLE:
            self.model=SentenceTransformer(model_name)

    def build(self, documents: list[Document]):
        self.documents=documents
        if EMBEDDINGS_AVAILABLE:
            vectors=self.model.encode([d.text for d in documents], normalize_embeddings=True, show_progress_bar=False)
            vectors=np.asarray(vectors,dtype='float32')
            self.index=faiss.IndexFlatIP(vectors.shape[1])
            self.index.add(vectors)
            faiss.write_index(self.index,str(self.index_dir/'faiss.index'))
        else:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer=TfidfVectorizer(stop_words='english',ngram_range=(1,2))
            self.matrix=self.vectorizer.fit_transform([d.text for d in documents])
        (self.index_dir/'documents.json').write_text(json.dumps([d.__dict__ for d in documents],ensure_ascii=False,indent=2),encoding='utf-8')
        (self.index_dir/'backend.txt').write_text('sentence-transformers + FAISS' if EMBEDDINGS_AVAILABLE else 'TF-IDF fallback',encoding='utf-8')

    def load(self):
        rows=json.loads((self.index_dir/'documents.json').read_text(encoding='utf-8'))
        self.documents=[Document(**r) for r in rows]
        backend=(self.index_dir/'backend.txt').read_text(encoding='utf-8').strip() if (self.index_dir/'backend.txt').exists() else ''
        if EMBEDDINGS_AVAILABLE and backend.startswith('sentence-transformers') and (self.index_dir/'faiss.index').exists():
            self.index=faiss.read_index(str(self.index_dir/'faiss.index'))
        else:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer=TfidfVectorizer(stop_words='english',ngram_range=(1,2))
            self.matrix=self.vectorizer.fit_transform([d.text for d in self.documents])

    def search(self,query:str,k:int=8):
        if not self.documents:
            self.load()
        if self.index is not None:
            q=self.model.encode([query],normalize_embeddings=True)
            scores,ids=self.index.search(np.asarray(q,dtype='float32'),k)
            return [(self.documents[i],float(score)) for score,i in zip(scores[0],ids[0]) if i>=0]
        from sklearn.metrics.pairwise import cosine_similarity
        q=self.vectorizer.transform([query])
        scores=cosine_similarity(q,self.matrix)[0]
        ids=scores.argsort()[::-1][:k]
        return [(self.documents[i],float(scores[i])) for i in ids]
