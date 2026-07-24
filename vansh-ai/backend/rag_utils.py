"""Small, dependency-light helpers for the RAG demo (handbook Day 16-17 in miniature)."""

import io

from pypdf import PdfReader


def extract_text_from_upload(filename: str, raw: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if lower.endswith((".txt", ".md")):
        return raw.decode("utf-8", errors="ignore")
    raise ValueError("Only .pdf, .txt, and .md files are supported in this demo.")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Simple sliding-window character chunker. Swap for a token-aware splitter
    (e.g. langchain's RecursiveCharacterTextSplitter) once you move past the demo."""
    text = " ".join(text.split())  # collapse whitespace
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c for c in chunks if len(c.strip()) > 30]
