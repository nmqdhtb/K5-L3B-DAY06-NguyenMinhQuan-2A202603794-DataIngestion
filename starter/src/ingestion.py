"""Read PDF pages without losing physical page numbers or paragraph boundaries."""
import logging
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader
from .models import DocumentPage


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Retain empty/failed pages with an explicit extraction status; never do OCR silently."""
    reader = PdfReader(path)
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        metadata = {}
        try:
            raw = page.extract_text() or ""
            text = normalize_text(raw)
            metadata.update(extraction_status="ok" if text else "empty",
                            raw_character_count=len(raw))
        except Exception as exc:
            logging.warning("Extraction failed: %s page %s: %s", document_id, number, exc)
            text = ""
            metadata.update(extraction_status="error", error=str(exc))
        if metadata["extraction_status"] == "empty":
            logging.warning("Empty text: %s page %s", document_id, number)
        pages.append(DocumentPage(document_id, source, number, text, metadata))
    return pages


def normalize_text(text: str) -> str:
    """Normalize Unicode/spacing only; edition-specific repairs belong in preparation."""
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
