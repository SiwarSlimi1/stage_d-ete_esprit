"""Extracteur pour le diplôme du baccalauréat (rapport §2.1)."""
from extraction.base_extractor import BaseExtractor, extract_after_label


class BacExtractor(BaseExtractor):
    document_type = "bac"
    required_fields = ["nom", "prenom", "annee_obtention"]

    def _extract_fields(self, text: str, lines: list[list[str]] | None = None) -> dict:
        return {
            "nom": extract_after_label(text, ["nom"]),
            "prenom": extract_after_label(text, ["prenom"]),
            "annee_obtention": extract_after_label(text, ["session", "annee d'obtention", "annee"]),
            "filiere_bac": extract_after_label(text, ["filiere"]),
            "mention": extract_after_label(text, ["mention"]),
        }
