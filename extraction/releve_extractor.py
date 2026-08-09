"""Extracteur pour les relevés de notes universitaires (rapport §2.1).

Contrairement aux autres documents, un relevé contient un tableau dense de
matières/notes dont la mise en page varie fortement (rapport §2.1, §8.1) : on
extrait ici les lignes restantes au format "Matière: note" une fois les champs
d'en-tête connus (année, étudiant, moyenne, résultat) identifiés et écartés.
"""
import re

from extraction.base_extractor import BaseExtractor, extract_after_label
from ocr.text_normalization import normalize

_HEADER_LABELS = {"annee universitaire", "etudiant", "moyenne generale", "moyenne", "resultat"}
_NOTE_PATTERN = re.compile(r"^(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:/20)?$")


def _extract_matieres(text: str) -> list[dict]:
    matieres = []
    for line in text.splitlines():
        delimiter = re.search(r"[:\-]", line)
        if not delimiter:
            continue
        key_raw = line[: delimiter.start()].strip()
        value = line[delimiter.end() :].strip()
        key_norm = normalize(key_raw)
        if not key_norm or key_norm in _HEADER_LABELS:
            continue
        match = _NOTE_PATTERN.match(value)
        if not match:
            continue
        matieres.append({"matiere": key_raw, "note": float(match.group(1).replace(",", "."))})
    return matieres


class ReleveExtractor(BaseExtractor):
    document_type = "releve_notes"
    required_fields = ["annee_universitaire", "moyenne"]

    def _extract_fields(self, text: str, lines: list[dict] | None = None, image=None) -> dict:
        return {
            "annee_universitaire": extract_after_label(text, ["annee universitaire"]),
            "etudiant": extract_after_label(text, ["etudiant"]),
            "matieres": _extract_matieres(text),
            "moyenne": extract_after_label(text, ["moyenne generale", "moyenne"]),
            "resultat": extract_after_label(text, ["resultat"]),
        }

    def _build_warnings(self, text: str, fields: dict) -> list[str]:
        warnings = []
        if "matieres" not in fields:
            warnings.append("aucune_matiere_detectee")
        return warnings
