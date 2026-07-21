"""Tests de la classification par règles (rapport §7.1)."""
import pytest

from classification.rules_classifier import DocumentClassifier

classifier = DocumentClassifier()


@pytest.mark.parametrize(
    "doc_type", ["cin", "acte_naissance", "bac", "diplome_licence", "releve_notes"]
)
def test_classify_recognizes_each_sample_type(sample_ocr_texts, doc_type):
    assert classifier.classify(sample_ocr_texts[doc_type]) == doc_type


def test_classify_with_confidence_is_high_on_clean_sample(sample_ocr_texts):
    result = classifier.classify_with_confidence(sample_ocr_texts["cin"])
    assert result["document_type"] == "cin"
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["confidence"] > 0.5


def test_classify_returns_unknown_for_irrelevant_text():
    assert classifier.classify("Ceci est un texte sans rapport avec un document.") == "inconnu"


def test_classify_returns_unknown_for_empty_text():
    assert classifier.classify("") == "inconnu"
