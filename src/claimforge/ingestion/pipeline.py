"""
ClaimForge AI — Ingestion: Pipeline
===================================

Turns raw files in a claim folder into ParsedDocument objects ready for the
extraction layer.

Week 1 scope: markdown (.md) and plain-text (.txt) files. Each becomes a
single-Page ParsedDocument (markdown has no native pages or pixel
coordinates). PDF and image handling — with multi-page parsing and
bounding boxes for citations — will be added when real PDFs arrive.

Public entry points:
    ingest_file(path)      -> ParsedDocument
    ingest_claim_folder(d) -> list[ParsedDocument]
"""
from __future__ import annotations

import hashlib
#from datetime import datetime
from datetime import datetime, timezone
from pathlib import Path

from claimforge.models import DocumentType, Page, ParsedDocument
from claimforge.ingestion.classifier import classify_document


# File extensions we can read as text in Week 1.
_SUPPORTED_TEXT_EXTENSIONS = {".md", ".txt"}

# Files we deliberately skip when scanning a claim folder.
_IGNORED_FILES = {"ground_truth.json", "readme.md", ".ds_store"}


def _sha256(text: str) -> str:
    """Content hash for idempotency / deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ingest_file(file_path: str | Path) -> ParsedDocument:
    """
    Read a single text file into a ParsedDocument.

    Args:
        file_path: path to a .md or .txt file.

    Returns:
        A ParsedDocument with one Page containing the full text.

    Raises:
        FileNotFoundError: if the path doesn't exist.
        ValueError: if the file type isn't supported in Week 1.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")

    if path.suffix.lower() not in _SUPPORTED_TEXT_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{path.suffix}' for {path.name}. "
            f"Week 1 ingestion supports {sorted(_SUPPORTED_TEXT_EXTENSIONS)}. "
            f"PDF/image support is added in a later phase."
        )

    text = path.read_text(encoding="utf-8")
    doc_type = classify_document(path, content=text)

    # Markdown/text = one logical page, no bounding boxes (those are for PDFs).
    page = Page(page_number=1, text=text, text_boxes=[], page_image_path=None)

    return ParsedDocument(
        source_file=str(path),
        document_type=doc_type,
        pages=[page],
        full_text=text,
        sha256=_sha256(text),
        #ingested_at=datetime.utcnow(),
        ingested_at=datetime.now(timezone.utc),
        metadata={
            "original_filename": path.name,
            "char_count": len(text),
            "ingestion_method": "text_passthrough_v1",
        },
    )


def ingest_claim_folder(folder_path: str | Path) -> list[ParsedDocument]:
    """
    Ingest every supported document in a claim folder.

    Skips ground_truth.json, READMEs, and OS junk files. Files are returned
    sorted by filename for deterministic ordering.

    Args:
        folder_path: path to a claim folder (e.g., data/claims/claim_001_covered).

    Returns:
        A list of ParsedDocument objects, one per supported file.

    Raises:
        FileNotFoundError: if the folder doesn't exist.
        NotADirectoryError: if the path isn't a directory.
    """
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"No such folder: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")

    documents: list[ParsedDocument] = []

    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        if path.name.lower() in _IGNORED_FILES:
            continue
        if path.suffix.lower() not in _SUPPORTED_TEXT_EXTENSIONS:
            # Silently skip unsupported types for now (e.g., a stray .json).
            continue
        documents.append(ingest_file(path))

    return documents
