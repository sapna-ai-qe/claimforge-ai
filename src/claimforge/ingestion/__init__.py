"""
ClaimForge AI — Ingestion Layer
===============================

Turns raw claim documents into normalized ParsedDocument objects.

Usage:
    from claimforge.ingestion import ingest_claim_folder, ingest_file, classify_document

    docs = ingest_claim_folder("data/claims/claim_001_covered")
    for doc in docs:
        print(doc.document_type, doc.source_file)
"""
from claimforge.ingestion.classifier import classify_document
from claimforge.ingestion.pipeline import ingest_claim_folder, ingest_file

__all__ = ["classify_document", "ingest_claim_folder", "ingest_file"]
