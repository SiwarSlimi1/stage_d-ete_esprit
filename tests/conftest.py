import pytest

from tests.sample_documents import generate_sample_documents


@pytest.fixture(scope="session")
def sample_documents():
    """Chemins des documents synthétiques d'exemple, générés une fois par session."""
    return generate_sample_documents()


@pytest.fixture(scope="session")
def sample_ocr_texts(sample_documents):
    """Texte OCR brut (après prétraitement) pour chaque document d'exemple."""
    from ocr.tesseract_engine import extract_text
    from preprocessing.image_utils import load_image, preprocess_pipeline

    texts = {}
    for doc_type, path in sample_documents.items():
        image = load_image(path)
        texts[doc_type] = extract_text(preprocess_pipeline(image))
    return texts
