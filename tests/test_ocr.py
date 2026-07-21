"""Tests OCR : mesure de la qualité d'extraction sur le jeu de documents d'exemple (rapport §7.1)."""
from ocr.text_normalization import normalize
from ocr.tesseract_engine import extract_text, extract_text_with_confidence
from preprocessing.image_utils import load_image, preprocess_pipeline

EXPECTED_KEYWORDS = {
    "cin": "carte d'identite nationale",
    "acte_naissance": "acte de naissance",
    "bac": "baccalaureat",
    "diplome_licence": "licence",
    "releve_notes": "releve de notes",
}


def test_extract_text_contains_expected_keyword(sample_documents):
    for doc_type, path in sample_documents.items():
        image = load_image(path)
        text = extract_text(preprocess_pipeline(image))
        assert EXPECTED_KEYWORDS[doc_type] in normalize(text)


def test_extract_text_with_confidence_returns_words_and_score(sample_documents):
    image = load_image(sample_documents["cin"])
    result = extract_text_with_confidence(preprocess_pipeline(image))
    assert result["words"], "l'OCR doit détecter au moins un mot"
    assert result["mean_confidence"] > 0
    assert "BEN" in result["text"].upper()
