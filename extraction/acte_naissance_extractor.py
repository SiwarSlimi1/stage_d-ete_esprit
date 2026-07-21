"""Extracteur pour l'acte de naissance (rapport §2.1)."""
import re

from extraction.base_extractor import BaseExtractor, extract_after_label
from ocr.text_normalization import normalize


def _extract_filiation(text: str) -> str | None:
    """Capture la filiation sur une ligne du type "Fille de: X et de Y" ou "Fils de X"."""
    for line in text.splitlines():
        normalized_line = normalize(line)
        match = re.search(r"(?:fille de|fils de|ne de|nee de)\s*:?\s*(.+)", normalized_line)
        if match:
            offset = match.start(1)
            return line[offset:].strip()
    return None


class ActeNaissanceExtractor(BaseExtractor):
    document_type = "acte_naissance"
    required_fields = ["nom", "prenom", "date_naissance"]

    def _extract_fields(self, text: str) -> dict:
        return {
            "nom": extract_after_label(text, ["nom"]),
            "prenom": extract_after_label(text, ["prenom"]),
            "date_naissance": extract_after_label(text, ["date de naissance", "nee le", "ne le"]),
            "lieu_naissance": extract_after_label(text, ["lieu de naissance"]),
            "filiation": _extract_filiation(text),
        }
