"""Extracteur pour l'acte de naissance (rapport §2.1)."""
import re

from extraction.base_extractor import (
    BaseExtractor,
    extract_after_label,
    extract_value_from_adjacent_line,
    extract_value_right_of_label,
)
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

    def _extract_fields(self, text: str, lines: list[dict] | None = None, image=None) -> dict:
        # 1) Format "Label: valeur" (documents propres, une ligne par champ).
        fields = {
            "nom": extract_after_label(text, ["nom"]),
            "prenom": extract_after_label(text, ["prenom"]),
            "date_naissance": extract_after_label(text, ["date de naissance", "nee le", "ne le"]),
            "lieu_naissance": extract_after_label(text, ["lieu de naissance"]),
            "filiation": _extract_filiation(text),
        }

        # 2) Repli positionnel pour les actes sous forme de tableau (extrait des
        # registres de l'état civil tunisien, version française) : le libellé et
        # sa valeur sont soit sur la même ligne ("PRENOMS MOUNIR"), soit séparés
        # sur deux lignes voisines lorsque l'analyse de mise en page les dissocie
        # ("NOM" seul, valeur juste avant).
        self._fields_from_positional_fallback = set()
        if lines:
            if not fields.get("prenom"):
                fields["prenom"] = extract_value_right_of_label(lines, ["prenoms", "prenom"])
                if fields["prenom"]:
                    self._fields_from_positional_fallback.add("prenom")

            if not fields.get("date_naissance"):
                fields["date_naissance"] = extract_value_right_of_label(lines, ["date de naissance"])
                if fields["date_naissance"]:
                    self._fields_from_positional_fallback.add("date_naissance")

            if not fields.get("nom"):
                fields["nom"] = extract_value_from_adjacent_line(lines, ["nom"])
                if fields["nom"]:
                    self._fields_from_positional_fallback.add("nom")

        return fields

    def _build_warnings(self, text: str, fields: dict) -> list[str]:
        estimated = getattr(self, "_fields_from_positional_fallback", set())
        if not estimated:
            return []
        champs = ", ".join(sorted(estimated))
        return [f"champs_estimes_par_position_tableau: {champs}"]
