"""Extracteur pour la carte d'identité nationale (rapport §2.1)."""
from difflib import SequenceMatcher

from extraction.base_extractor import (
    BaseExtractor,
    extract_after_label,
    extract_standalone_number,
    extract_value_left_of_label,
)
from ocr.text_normalization import normalize

# Libellés arabes imprimés sur une CIN tunisienne, avec variantes tolérant les
# erreurs de lecture courantes de l'OCR sur ce script (rapport §2.2.1, §8.3).
_ARABIC_LABELS = {
    "nom": ["اللقب"],
    "prenom": ["الاسم"],
    "date_naissance": ["تاريخ الولادة"],
    "lieu_naissance": ["مكان الولادة", "مكانها"],
    "nationalite": ["الجنسية"],
}


def _extract_nom_from_line_before_prenom(lines: list[list[str]], threshold: float = 0.7) -> str | None:
    """Repli quand le libellé "اللقب" (nom) n'est pas reconnu par l'OCR - fréquent
    en pratique, ce libellé étant imprimé en petit sur la carte.

    Sur le gabarit officiel de la CIN tunisienne, le champ nom précède toujours
    immédiatement le champ prénom. Si le libellé du prénom ("الاسم") est repéré de
    façon fiable, la ligne précédente est donc, par construction du document, celle
    du nom : on en retire le dernier mot (le libellé du nom, même s'il n'a pas pu
    être identifié tel quel) pour ne garder que sa valeur.
    """
    for i, words in enumerate(lines):
        if i == 0 or len(words) < 2:
            continue
        tail_rtl = normalize(words[-1])
        if SequenceMatcher(None, tail_rtl, normalize("الاسم")).ratio() >= threshold:
            previous_words = lines[i - 1]
            if len(previous_words) >= 2:
                return " ".join(reversed(previous_words[:-1]))
    return None


class CINExtractor(BaseExtractor):
    document_type = "cin"
    required_fields = ["nom", "prenom", "date_naissance", "numero_document"]

    def _extract_fields(self, text: str, lines: list[list[str]] | None = None) -> dict:
        # 1) Format "Label: valeur" (documents propres, français) - stratégie principale.
        fields = {
            "nom": extract_after_label(text, ["nom"]),
            "prenom": extract_after_label(text, ["prenom"]),
            "date_naissance": extract_after_label(text, ["date de naissance", "nee le", "ne le"]),
            "lieu_naissance": extract_after_label(text, ["lieu de naissance"]),
            "nationalite": extract_after_label(text, ["nationalite"]),
            "numero_document": extract_after_label(
                text, ["n cin", "numero cin", "cin n", "n carte", "numero de la carte"]
            ),
        }

        # 2) Repli positionnel pour les CIN en arabe (libellé à droite, valeur à
        # gauche sur la même ligne) : ne s'applique qu'aux champs encore vides et
        # seulement si les données positionnelles (lines) sont disponibles. Les
        # champs comblés par ce repli sont mémorisés pour signaler, via un
        # avertissement, qu'ils sont moins fiables qu'une correspondance directe.
        self._fields_from_positional_fallback = set()

        if lines:
            for field_name, label_variants in _ARABIC_LABELS.items():
                if not fields.get(field_name):
                    value = extract_value_left_of_label(lines, label_variants)
                    if value:
                        fields[field_name] = value
                        self._fields_from_positional_fallback.add(field_name)

            if not fields.get("numero_document"):
                value = extract_standalone_number(lines)
                if value:
                    fields["numero_document"] = value
                    self._fields_from_positional_fallback.add("numero_document")

            # 3) Dernier repli pour "nom" : le libellé "اللقب" est rarement bien
            # reconnu par l'OCR (police décorative, petite taille) - on se rabat sur
            # sa position connue, juste avant la ligne du prénom.
            if not fields.get("nom"):
                value = _extract_nom_from_line_before_prenom(lines)
                if value:
                    fields["nom"] = value
                    self._fields_from_positional_fallback.add("nom")

        return fields

    def _build_warnings(self, text: str, fields: dict) -> list[str]:
        estimated = getattr(self, "_fields_from_positional_fallback", set())
        if not estimated:
            return []
        champs = ", ".join(sorted(estimated))
        return [f"champs_estimes_par_position_carte_arabe: {champs}"]
