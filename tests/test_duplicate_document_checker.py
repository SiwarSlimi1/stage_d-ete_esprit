"""Tests de la détection de documents dupliqués (rapport §9)."""
from verification.duplicate_document_checker import check_duplicate_documents


def test_identical_documents_are_flagged():
    text = "RELEVE DE NOTES\nAnnee universitaire: 2022/2023\nMoyenne generale: 13.8"
    documents = [
        {"label": "Relevé — L2", "raw_text": text},
        {"label": "Relevé — L2 (bis)", "raw_text": text},
    ]
    result = check_duplicate_documents(documents)
    assert result["consistent"] is False
    assert "Relevé — L2" in result["issues"][0]


def test_different_documents_are_not_flagged():
    documents = [
        {"label": "CIN", "raw_text": "CARTE D'IDENTITE NATIONALE\nNom: BEN ALI\nPrenom: SALMA"},
        {"label": "Bac", "raw_text": "DIPLOME DU BACCALAUREAT\nNom: BEN ALI\nSession: 2019"},
    ]
    result = check_duplicate_documents(documents)
    assert result["consistent"] is True


def test_empty_or_missing_raw_text_is_ignored():
    documents = [
        {"label": "CIN", "raw_text": ""},
        {"label": "Bac", "raw_text": None},
    ]
    result = check_duplicate_documents(documents)
    assert result["consistent"] is True
    assert result["issues"] == []
