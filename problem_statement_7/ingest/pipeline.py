"""Full ingestion pipeline: PDF → entities → DB + vector store."""
from tqdm import tqdm
from rich.console import Console

from ingest.pdf_extractor import extract_all
from ingest.entity_extractor import extract_entities
from db.loader import upsert_document
from vectors.store import add_document
from config import PDF_FOLDER

console = Console()

def run(pdf_folder: str = PDF_FOLDER):
    console.print(f"[bold cyan]Extracting PDFs from {pdf_folder}[/bold cyan]")
    docs = extract_all(pdf_folder)
    console.print(f"[green]Found {len(docs)} documents[/green]")

    for doc in tqdm(docs, desc="Processing"):
        entities = extract_entities(doc["filename"], doc["raw_text"])
        entities["filename"]  = doc["filename"]
        entities["file_path"] = doc["path"]
        entities["raw_text"]  = doc["raw_text"]
        upsert_document(entities)
        add_document(
            doc_id=doc["filename"],
            text=doc["raw_text"],
            metadata={
                "filename":   doc["filename"],
                "doc_type":   entities.get("doc_type", "unknown"),
                "truck_unit": str(entities.get("truck_unit") or ""),
                "driver":     str(entities.get("driver_name") or ""),
                "date":       str(entities.get("date") or ""),
            }
        )

    console.print("[bold green]✓ Ingestion complete[/bold green]")
