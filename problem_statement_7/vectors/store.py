"""ChromaDB vector store with sentence-transformers embeddings."""
import threading
import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_PATH

_lock       = threading.Lock()
_client     = None
_collection = None

def _get_collection():
    global _client, _collection
    if _collection is None:
        with _lock:
            if _collection is None:
                _client = chromadb.PersistentClient(path=CHROMA_PATH)
                ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                _collection = _client.get_or_create_collection(
                    name="fleet_docs",
                    embedding_function=ef,
                    metadata={"hnsw:space": "cosine"}
                )
    return _collection


def add_document(doc_id: str, text: str, metadata: dict):
    col = _get_collection()
    chunks = _chunk_text(text, max_chars=1500)
    for i, chunk in enumerate(chunks):
        col.upsert(
            ids=[f"{doc_id}::chunk{i}"],
            documents=[chunk],
            metadatas=[{**metadata, "chunk": i}]
        )


def search(query: str, n_results: int = 5, where: dict = None) -> list[dict]:
    col = _get_collection()
    n_results = min(n_results, col.count()) if col.count() > 0 else 1
    kwargs = {"query_texts": [query], "n_results": n_results}
    if where:
        kwargs["where"] = where
    results = col.query(**kwargs)
    out = []
    for i, doc in enumerate(results["documents"][0]):
        out.append({
            "text":     doc,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return out


def _chunk_text(text: str, max_chars: int = 1500) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = start + max_chars
        if end < len(text):
            break_at = text.rfind("\n", start, end)
            if break_at > start:
                end = break_at
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]
