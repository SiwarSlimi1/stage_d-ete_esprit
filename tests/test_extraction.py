"""Tests des extracteurs spécialisés et du contrat JSON commun (rapport §7.1, §3.2.4)."""
from extraction import get_extractor
from extraction.cin_extractor import CINExtractor

CONTRACT_KEYS = {"document_type", "fields", "missing_fields", "warnings", "extraction_status"}


def test_extraction_contract_has_expected_keys(sample_ocr_texts):
    result = CINExtractor().extract(sample_ocr_texts["cin"])
    assert set(result.keys()) == CONTRACT_KEYS


def test_cin_extractor_on_sample(sample_ocr_texts):
    result = get_extractor("cin").extract(sample_ocr_texts["cin"])
    assert result["extraction_status"] == "success"
    assert result["fields"]["nom"] == "BEN ALI"
    assert result["fields"]["prenom"] == "SALMA"
    assert result["fields"]["numero_document"] == "08453219"
    assert result["missing_fields"] == []


def test_acte_naissance_extractor_on_sample(sample_ocr_texts):
    result = get_extractor("acte_naissance").extract(sample_ocr_texts["acte_naissance"])
    assert result["extraction_status"] == "success"
    assert result["fields"]["nom"] == "BEN ALI"
    assert "TRABELSI" in result["fields"]["filiation"]


def test_bac_extractor_on_sample(sample_ocr_texts):
    result = get_extractor("bac").extract(sample_ocr_texts["bac"])
    assert result["extraction_status"] == "success"
    assert result["fields"]["annee_obtention"] == "2019"
    assert result["fields"]["mention"] == "ASSEZ BIEN"


def test_licence_extractor_on_sample(sample_ocr_texts):
    result = get_extractor("diplome_licence").extract(sample_ocr_texts["diplome_licence"])
    assert result["extraction_status"] == "success"
    assert result["fields"]["specialite"] == "INFORMATIQUE DE GESTION"
    assert result["fields"]["annee_obtention"] == "2024"


def test_releve_extractor_on_sample(sample_ocr_texts):
    result = get_extractor("releve_notes").extract(sample_ocr_texts["releve_notes"])
    assert result["extraction_status"] == "success"
    assert result["fields"]["annee_universitaire"] == "2022/2023"
    assert len(result["fields"]["matieres"]) == 3
    assert result["fields"]["resultat"] == "VALIDE"


def test_extraction_status_is_failed_when_no_field_found():
    result = CINExtractor().extract("Texte quelconque sans aucun champ reconnaissable.")
    assert result["extraction_status"] == "failed"
    assert result["fields"] == {}
    assert set(result["missing_fields"]) == set(CINExtractor.required_fields)


def test_extraction_status_is_partial_when_some_required_fields_missing():
    text = "Nom: BEN ALI\nPrenom: SALMA"
    result = CINExtractor().extract(text)
    assert result["extraction_status"] == "partial"
    assert "date_naissance" in result["missing_fields"]
    assert "numero_document" in result["missing_fields"]


def test_get_extractor_returns_none_for_unknown_type():
    assert get_extractor("inconnu") is None
