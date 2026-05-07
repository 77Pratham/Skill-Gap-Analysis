"""
Resume Parser
Extracts raw text from resume files: PDF, DOCX, or plain text.
"""

import io
import re
from typing import Tuple


def parse_resume(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """
    Parse resume file and return (text, candidate_name).
    Returns empty string if parsing fails.
    """
    filename_lower = filename.lower()
    text = ""

    try:
        if filename_lower.endswith(".pdf"):
            text = _parse_pdf(file_bytes)
        elif filename_lower.endswith((".docx", ".doc")):
            text = _parse_docx(file_bytes)
        else:
            # Assume plain text
            text = file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        text = ""

    # Clean text
    text = _clean_text(text)

    # Extract candidate name (first non-empty line, if looks like a name)
    candidate_name = _extract_name(text, filename)

    return text, candidate_name


def _parse_pdf(file_bytes: bytes) -> str:
    import pdfplumber
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def _parse_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _clean_text(text: str) -> str:
    """Normalise whitespace, remove control characters."""
    # Remove non-printable characters
    text = re.sub(r"[^\x20-\x7E\n\t]", " ", text)
    # Collapse multiple spaces
    text = re.sub(r" {3,}", "  ", text)
    # Collapse multiple newlines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _extract_name(text: str, filename: str) -> str:
    """Heuristically extract candidate name from text or filename."""
    # Try first non-empty line (common resume format)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        first_line = lines[0]
        # A name is typically 2-4 words, no digits, not too long
        words = first_line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w) and not any(char.isdigit() for char in first_line):
            return first_line

    # Fallback: use filename without extension
    name = filename.rsplit(".", 1)[0]
    name = re.sub(r"[_\-]", " ", name).strip().title()
    return name if len(name) > 1 else "Candidate"
