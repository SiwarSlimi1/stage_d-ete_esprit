"""Test fonctionnel de bout en bout du pipeline Sprint 1 & 2 (rapport §7.1).

prétraitement -> OCR -> classification -> extraction, sur chaque document d'exemple.
"""
import pytest

from main import process_document


@pytest.mark.parametrize(
    "doc_type", ["cin", "acte_naissance", "bac", "diplome_licence", "releve_notes"]
)
def test_process_document_end_to_end(sample_documents, doc_type):
    result = process_document(sample_documents[doc_type])

    assert result["document_type"] == doc_type
    assert result["extraction_status"] == "success"
    assert result["classification_confidence"] > 0.5
    assert result["missing_fields"] == []
    if "nom" in result["fields"]:
        assert result["fields"]["nom"] == "BEN ALI"
