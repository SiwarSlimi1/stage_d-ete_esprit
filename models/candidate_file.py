"""Structures de données partagées entre les modules (rapport §3.5, diagramme de classes)."""
from dataclasses import dataclass, field


@dataclass
class Document:
    """Un document déposé par le candidat, à un instant donné du pipeline."""

    image_path: str
    raw_text: str = ""
    doc_type: str = "inconnu"
    classification_confidence: float = 0.0

    def preprocess(self):
        from preprocessing.image_utils import load_image, preprocess_pipeline

        image = load_image(self.image_path)
        return preprocess_pipeline(image)

    def run_ocr(self, processed_image) -> None:
        from ocr.tesseract_engine import extract_text

        self.raw_text = extract_text(processed_image)


@dataclass
class ExtractionResult:
    """Sortie standardisée d'un extracteur, conforme au contrat JSON (rapport §3.2.4)."""

    document_type: str
    fields: dict = field(default_factory=dict)
    missing_fields: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    extraction_status: str = "failed"

    def to_dict(self) -> dict:
        return {
            "document_type": self.document_type,
            "fields": self.fields,
            "missing_fields": self.missing_fields,
            "warnings": self.warnings,
            "extraction_status": self.extraction_status,
        }


@dataclass
class CandidateFile:
    """Dossier complet d'un candidat, agrégeant tous ses documents.

    completeness_score et status sont calculés par le module de scoring (Sprint 3) ;
    ils sont initialisés ici à une valeur neutre car non couverts par Sprint 1/2.
    """

    candidate_id: str
    documents: list[Document] = field(default_factory=list)
    completeness_score: float = 0.0
    status: str = "non_evalue"

    def add_document(self, document: Document) -> None:
        self.documents.append(document)
