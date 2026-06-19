#!/usr/bin/env python3
"""
FleetOS — Two-stage ingestion pipeline.
Stage 1: Parallel PDF extraction + entity extraction (12 workers)
Stage 2: Single-threaded DB writes + vector indexing (avoids DuckDB conflicts)
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from rich.console import Console
from collections import Counter

from db.schema import init_schema
from ingest.pdf_extractor import extract_all
from ingest.entity_extractor import extract_entities
from db.loader import upsert_document
from vectors.store import add_document
from config import PDF_FOLDER

console = Console()

def extract_one(doc: dict) -> dict:
    """Stage 1: extract text already done; just run entity extraction."""
    entities = extract_entities(doc["filename"], doc["raw_text"])
    entities.update({"filename": doc["filename"], "file_path": doc["path"],
                     "raw_text": doc["raw_text"]})
    return entities


if __name__ == "__main__":
    init_schema()   # called ONCE before any threads start
    console.print(f"[bold cyan]Scanning PDFs from:[/bold cyan] {PDF_FOLDER}")
    docs = extract_all(PDF_FOLDER)
    console.print(f"[green]Found {len(docs)} documents[/green]")

    # ── Stage 1: parallel extraction ──────────────────────────────────────
    all_entities = []
    errors = []
    console.print("[bold]Stage 1:[/bold] Parallel entity extraction (12 workers)...")
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(extract_one, doc): doc["filename"] for doc in docs}
        with tqdm(total=len(futures), desc="Extracting") as bar:
            for fut in as_completed(futures):
                fname = futures[fut]
                try:
                    all_entities.append(fut.result())
                except Exception as e:
                    errors.append(f"{fname}: {e}")
                bar.update(1)

    # ── Stage 2: single-threaded writes ───────────────────────────────────
    console.print("[bold]Stage 2:[/bold] Loading into DuckDB + ChromaDB...")
    write_errors = []
    for entities in tqdm(all_entities, desc="Writing"):
        try:
            upsert_document(entities)
            add_document(
                doc_id=entities["filename"],
                text=entities["raw_text"],
                metadata={
                    "filename":   entities["filename"],
                    "doc_type":   entities.get("doc_type","unknown"),
                    "truck_unit": str(entities.get("truck_unit") or ""),
                    "driver":     str(entities.get("driver_name") or ""),
                    "date":       str(entities.get("date") or ""),
                }
            )
        except Exception as e:
            write_errors.append(f"{entities['filename']}: {e}")

    total_err = len(errors) + len(write_errors)
    console.print(f"\n[bold green]✓ Done:[/bold green] {len(all_entities)-len(write_errors)}/197 loaded successfully")
    if total_err:
        for e in (errors+write_errors)[:5]:
            console.print(f"  [red]✗[/red] {e}")

    console.print("\n[bold]Document types:[/bold]")
    counts = Counter(e.get("doc_type","unknown") for e in all_entities)
    for t,n in sorted(counts.items(), key=lambda x:-x[1]):
        console.print(f"  {t:35s} {n:4d}")
