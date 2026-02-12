"""
Document Loader Module
======================
Accepts PDF or plain-text files and returns clean raw text.

Responsibilities:
    - Detect file type (PDF vs TXT)
    - Extract text from PDFs using pdfplumber (fallback: PyPDF2)
    - Read plain-text files directly
    - Return the full document text as a string

No business logic lives here — this is purely I/O.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def load_document(file_path: str) -> str:
    """
    Load a document from *file_path* and return its text content.

    Supported formats:
        - .pdf  → extracted via pdfplumber (with PyPDF2 fallback)
        - .txt  → read directly as UTF-8 text

    Raises:
        FileNotFoundError: if the path does not exist.
        ValueError:        if the extension is unsupported.

    Returns:
        Raw text extracted from the document.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    ext = path.suffix.lower()
    logger.info("Loading document: %s (type: %s)", path.name, ext)

    if ext == ".pdf":
        return _extract_pdf_text(path)
    elif ext == ".txt":
        return _extract_txt_text(path)
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported types: .pdf, .txt"
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file using pdfplumber, falling back to PyPDF2."""
    text = _try_pdfplumber(path)
    if text and text.strip():
        return text.strip()

    logger.warning("pdfplumber returned empty text; falling back to PyPDF2.")
    text = _try_pypdf2(path)
    if text and text.strip():
        return text.strip()

    logger.error("Could not extract text from PDF: %s", path.name)
    return ""


def _try_pdfplumber(path: Path) -> str:
    """Attempt extraction with pdfplumber."""
    try:
        import pdfplumber

        pages: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("pdfplumber is not installed; skipping.")
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdfplumber failed: %s", exc)
        return ""


def _try_pypdf2(path: Path) -> str:
    """Attempt extraction with PyPDF2."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("PyPDF2 is not installed; skipping.")
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("PyPDF2 failed: %s", exc)
        return ""


def _extract_txt_text(path: Path) -> str:
    """Read a plain-text file."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        logger.warning("UTF-8 decode failed; trying latin-1.")
        return path.read_text(encoding="latin-1").strip()
