"""Extracteur pour le diplôme de licence (rapport §2.1)."""
from extraction.base_extractor import BaseExtractor, extract_after_label


class LicenceExtractor(BaseExtractor):
    document_type = "diplome_licence"
    required_fields = ["nom", "prenom", "specialite", "annee_obtention"]

    def _extract_fields(self, text: str, lines: list[dict] | None = None, image=None) -> dict:
        return {
            "nom": extract_after_label(text, ["nom"]),
            "prenom": extract_after_label(text, ["prenom"]),
            "specialite": extract_after_label(text, ["specialite"]),
            "annee_obtention": extract_after_label(text, ["annee d'obtention", "annee"]),
            "etablissement": extract_after_label(text, ["etablissement"]),
        }
