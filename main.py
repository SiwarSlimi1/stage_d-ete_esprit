"""Point d'entrée du pipeline (rapport §3.4, Sprint 1 & 2) :

    prétraitement (OpenCV) -> OCR (Tesseract) -> classification (règles) -> extraction

La vérification de cohérence, le score de complétude et la génération de
questions d'entretien relèvent du Sprint 3 et ne sont pas exécutées ici.
"""
import json
from datetime import datetime
from pathlib import Path

from classification.rules_classifier import DocumentClassifier
from config.settings import REPORTS_DIR, SAMPLES_DIR
from extraction import get_extractor
from models.candidate_file import Document
from ocr.tesseract_engine import extract_text
from preprocessing.image_utils import load_image, preprocess_pipeline

classifier = DocumentClassifier()


def process_document(image_path: Path) -> dict:
    """Exécute la chaîne prétraitement -> OCR -> classification -> extraction
    pour un document unique et retourne le contrat JSON correspondant."""
    document = Document(image_path=str(image_path))

    processed_image = document.preprocess()
    document.run_ocr(processed_image)

    classification = classifier.classify_with_confidence(document.raw_text)
    document.doc_type = classification["document_type"]
    document.classification_confidence = classification["confidence"]

    extractor = get_extractor(document.doc_type)
    if extractor is None:
        return {
            "document_type": document.doc_type,
            "fields": {},
            "missing_fields": [],
            "warnings": ["type_de_document_non_reconnu"],
            "extraction_status": "failed",
            "classification_confidence": document.classification_confidence,
            "source_image": str(image_path),
        }

    result = extractor.extract(document.raw_text, document.word_lines)
    result["classification_confidence"] = document.classification_confidence
    result["source_image"] = str(image_path)
    return result


def process_directory(samples_dir: Path = SAMPLES_DIR) -> list[dict]:
    image_paths = sorted(p for p in samples_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    return [process_document(path) for path in image_paths]


def main() -> None:
    results = process_directory()

    for result in results:
        print(f"--- {Path(result['source_image']).name} ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    report_path = REPORTS_DIR / f"rapport_{datetime.now():%Y%m%d_%H%M%S}.json"
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRapport agrégé écrit dans : {report_path}")


if __name__ == "__main__":
    main()
