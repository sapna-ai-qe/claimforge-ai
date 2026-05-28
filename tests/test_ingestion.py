"""
Tests for the ingestion layer.

Run with:  pytest tests/test_ingestion.py -v

These tests assume the sample data exists at data/claims/claim_001_covered/.
"""
from pathlib import Path

import pytest

from claimforge.ingestion import classify_document, ingest_claim_folder, ingest_file
from claimforge.models import DocumentType


# Resolve the repo root so tests work regardless of where pytest is invoked.
REPO_ROOT = Path(__file__).resolve().parent.parent
CLAIM_001 = REPO_ROOT / "data" / "claims" / "claim_001_covered"


# ----------------------------------------------------------------------
# Classification
# ----------------------------------------------------------------------

@pytest.mark.parametrize("filename,expected", [
    ("fnol.md", DocumentType.FNOL),
    ("police_report.md", DocumentType.POLICE_REPORT),
    ("repair_estimate.md", DocumentType.ESTIMATE),
    ("damage_photos.md", DocumentType.PHOTO),
    ("adjuster_investigation_note.md", DocumentType.STATEMENT),
    ("constellation_auto_policy_v1.md", DocumentType.POLICY),
    ("totally_random_name.md", DocumentType.UNKNOWN),
])
def test_classify_by_filename(filename, expected):
    assert classify_document(filename) == expected


def test_classify_by_content_fallback():
    """A generically-named file is classified by its content."""
    content = "# CITY POLICE DEPARTMENT\n## MOTOR VEHICLE CRASH REPORT\nReporting Officer: X"
    assert classify_document("doc1.md", content=content) == DocumentType.POLICE_REPORT


def test_classify_unknown_when_no_signal():
    assert classify_document("doc1.md", content="just some text") == DocumentType.UNKNOWN


# ----------------------------------------------------------------------
# Single-file ingestion
# ----------------------------------------------------------------------

@pytest.mark.skipif(not CLAIM_001.exists(), reason="sample data not present")
def test_ingest_single_file():
    doc = ingest_file(CLAIM_001 / "fnol.md")
    assert doc.document_type == DocumentType.FNOL
    assert len(doc.pages) == 1
    assert doc.pages[0].page_number == 1
    assert len(doc.full_text) > 0
    assert len(doc.sha256) == 64           # sha256 hex digest length
    assert "char_count" in doc.metadata
    assert doc.document_id                  # auto-assigned, non-empty


def test_ingest_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        ingest_file("does/not/exist.md")


def test_ingest_unsupported_type_raises(tmp_path):
    bad = tmp_path / "scan.pdf"
    bad.write_text("not really a pdf")
    with pytest.raises(ValueError):
        ingest_file(bad)


def test_ingestion_is_idempotent():
    """Same content always yields the same hash (dedup key)."""
    sample = REPO_ROOT / "tests" / "_tmp_idempotency.md"
    sample.write_text("# FNOL\nsome content", encoding="utf-8")
    try:
        h1 = ingest_file(sample).sha256
        h2 = ingest_file(sample).sha256
        assert h1 == h2
    finally:
        sample.unlink(missing_ok=True)


# ----------------------------------------------------------------------
# Folder ingestion
# ----------------------------------------------------------------------

@pytest.mark.skipif(not CLAIM_001.exists(), reason="sample data not present")
def test_ingest_claim_folder():
    docs = ingest_claim_folder(CLAIM_001)
    # ground_truth.json must be skipped; the 4 markdown docs ingested.
    assert len(docs) == 4
    assert all(d.document_type != DocumentType.UNKNOWN for d in docs)
    assert all("ground_truth" not in d.source_file for d in docs)


def test_ingest_missing_folder_raises():
    with pytest.raises(FileNotFoundError):
        ingest_claim_folder("data/claims/does_not_exist")
