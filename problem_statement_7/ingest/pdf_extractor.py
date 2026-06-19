"""Extract raw text from PDFs."""
from pathlib import Path
import pdfplumber


def extract_text(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts).strip()


def extract_all(folder: str) -> list[dict]:
    results = []
    for p in sorted(Path(folder).glob("*.pdf")):
        try:
            text = extract_text(str(p))
            results.append({"filename": p.name, "path": str(p), "raw_text": text})
        except Exception as e:
            print(f"[WARN] {p.name}: {e}")
    return results
