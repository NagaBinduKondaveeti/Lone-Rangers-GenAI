"""Retrieve relevant document chunks from ChromaDB."""
from vectors.store import search


def retrieve(question: str, n_results: int = 5) -> list[dict]:
    return search(question, n_results=n_results)


def format_context(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        meta = c["metadata"]
        parts.append(
            f"[{meta.get('filename','')} | type={meta.get('doc_type','')} | "
            f"truck={meta.get('truck_unit','')} | date={meta.get('date','')}]\n{c['text']}"
        )
    return "\n\n---\n\n".join(parts)
