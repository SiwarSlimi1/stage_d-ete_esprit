"""Extracteur pour la carte d'identité nationale (rapport §2.1)."""
from extraction.base_extractor import BaseExtractor, extract_after_label


class CINExtractor(BaseExtractor):
    document_type = "cin"
    required_fields = ["nom", "prenom", "date_naissance", "numero_document"]

    def _extract_fields(self, text: str) -> dict:
        return {
            "nom": extract_after_label(text, ["nom"]),
            "prenom": extract_after_label(text, ["prenom"]),
            "date_naissance": extract_after_label(text, ["date de naissance", "nee le", "ne le"]),
            "lieu_naissance": extract_after_label(text, ["lieu de naissance"]),
            "nationalite": extract_after_label(text, ["nationalite"]),
            "numero_document": extract_after_label(
                text, ["n cin", "numero cin", "cin n", "n carte", "numero de la carte"]
            ),
        }
