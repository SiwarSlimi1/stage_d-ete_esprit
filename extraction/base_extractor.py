"""Interface commune des extracteurs et contrat JSON partagé (rapport §3.2.4).

Chaque extracteur spécialisé hérite de BaseExtractor et implémente uniquement
_extract_fields(). La méthode extract() applique le contrat de sortie commun :

{
  "document_type": str,
  "fields": dict,
  "missing_fields": list[str],
  "warnings": list[str],
  "extraction_status": "success" | "partial" | "failed"
}
"""
import re
from abc import ABC, abstractmethod

from ocr.text_normalization import normalize


def extract_after_label(text: str, labels: list[str]) -> str | None:
    """Cherche une ligne au format "Label: valeur" et retourne la valeur.

    Le label est comparé sous forme normalisée (minuscules, sans accents) contre
    la partie de la ligne précédant le premier ':' ou '-', afin d'éviter qu'un
    label ne matche par erreur à l'intérieur d'un autre (ex. "nom" dans "prenom").
    """
    for line in text.splitlines():
        delimiter = re.search(r"[:\-]", line)
        if not delimiter:
            continue
        key_part = normalize(line[: delimiter.start()]).strip()
        value_part = line[delimiter.end() :].strip()
        if not value_part:
            continue
        for label in labels:
            if key_part == label:
                return value_part
    return None


def find_pattern(text: str, pattern: str) -> str | None:
    """Recherche un motif regex libre dans le texte brut (insensible à la casse)."""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


class BaseExtractor(ABC):
    """Interface commune de tous les extracteurs spécialisés (rapport §3.5)."""

    document_type: str = ""
    required_fields: list[str] = []

    @abstractmethod
    def _extract_fields(self, text: str) -> dict:
        """Extrait les champs propres au type de document depuis le texte OCR brut."""

    def _build_warnings(self, text: str, fields: dict) -> list[str]:
        return []

    def extract(self, text: str) -> dict:
        fields = {k: v for k, v in self._extract_fields(text).items() if v}
        missing_fields = [f for f in self.required_fields if not fields.get(f)]
        warnings = self._build_warnings(text, fields)

        if not missing_fields:
            status = "success"
        elif fields:
            status = "partial"
        else:
            status = "failed"

        return {
            "document_type": self.document_type,
            "fields": fields,
            "missing_fields": missing_fields,
            "warnings": warnings,
            "extraction_status": status,
        }
