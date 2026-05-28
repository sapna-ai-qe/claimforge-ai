"""
ClaimForge AI — Ingestion: Document Classifier
==============================================

Determines the DocumentType of a file from its filename and content.

For Week 1 (markdown sample data), classification is rule-based: filename
keywords first, content keywords as a fallback. No LLM needed.

When real PDFs/images arrive, this is where a small vision-LLM classifier
would be added as a final fallback for ambiguous documents.
"""
from __future__ import annotations

from pathlib import Path

from claimforge.models import DocumentType


# Filename keyword → DocumentType. Checked first; fast and deterministic.
_FILENAME_KEYWORDS: list[tuple[tuple[str, ...], DocumentType]] = [
    (("fnol", "first_notice", "notice_of_loss"), DocumentType.FNOL),
    (("police", "crash_report", "accident_report"), DocumentType.POLICE_REPORT),
    (("estimate", "repair"), DocumentType.ESTIMATE),
    (("photo", "image", "damage_photo"), DocumentType.PHOTO),
    (("policy", "declarations", "dec_page"), DocumentType.POLICY),
    (("medical", "bill", "invoice"), DocumentType.MEDICAL_BILL),
    (("statement", "investigation", "adjuster_note"), DocumentType.STATEMENT),
]

# Content keyword → DocumentType. Fallback when filename is uninformative.
# Order matters: more specific signals first.
_CONTENT_KEYWORDS: list[tuple[tuple[str, ...], DocumentType]] = [
    (("first notice of loss", "fnol"), DocumentType.FNOL),
    (("motor vehicle crash report", "police department", "reporting officer"),
     DocumentType.POLICE_REPORT),
    (("repair estimate", "estimate id", "line items", "estimate total"),
     DocumentType.ESTIMATE),
    (("damage photos", "photo capture", "filename:"), DocumentType.PHOTO),
    (("personal auto policy", "declarations page", "insuring agreement"),
     DocumentType.POLICY),
    (("medical", "cpt", "icd-10", "provider"), DocumentType.MEDICAL_BILL),
    (("investigation note", "adjuster", "recorded statement"),
     DocumentType.STATEMENT),
]


def classify_document(file_path: str | Path, content: str | None = None) -> DocumentType:
    """
    Classify a document by filename, then by content if needed.

    Args:
        file_path: path to the file (its name is the primary signal).
        content: the file's text content (used as a fallback). If None,
                 only the filename is used.

    Returns:
        The best-guess DocumentType, or DocumentType.UNKNOWN if no rule matches.
    """
    name = Path(file_path).name.lower()

    # 1. Filename keywords (fast, deterministic, usually sufficient)
    for keywords, doc_type in _FILENAME_KEYWORDS:
        if any(kw in name for kw in keywords):
            return doc_type

    # 2. Content keywords (fallback for generically-named files)
    if content:
        lowered = content.lower()
        for keywords, doc_type in _CONTENT_KEYWORDS:
            if any(kw in lowered for kw in keywords):
                return doc_type

    return DocumentType.UNKNOWN
