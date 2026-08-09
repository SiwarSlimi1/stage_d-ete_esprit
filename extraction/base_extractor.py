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
from difflib import SequenceMatcher

import numpy as np

from ocr.text_normalization import normalize

# Une "ligne" positionnelle, telle que produite par ocr.tesseract_engine.extract_lines :
# {"words": list[str], "top": int, "bottom": int, "left": int, "right": int}
Line = dict


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


def _similar(a: str, b: str, threshold: float = 0.7) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= threshold


def _strip_footnote_marks(value: str) -> str:
    """Retire les marqueurs de renvoi ('*' imprimé sur le formulaire, souvent lu
    '®' ou '©' par l'OCR) en fin de valeur."""
    return re.sub(r"[\*®©\s]+$", "", value).strip()


def extract_value_left_of_label(lines: list[Line], label_variants: list[str]) -> str | None:
    """Extraction positionnelle pour les documents en écriture arabe (RTL).

    Sur une carte d'identité tunisienne, le libellé d'un champ (ex. "الاسم") est
    imprimé à droite de sa valeur, sur la même ligne. Le texte OCR brut linéaire
    ne permet pas de retrouver cette relation ; les coordonnées des mots le
    permettent : chaque ligne fournit ses mots triés de gauche à droite
    (coordonnées image). Le libellé correspond donc aux derniers mots de la
    ligne, et la valeur - une fois ces mots retirés - doit être relue dans
    l'ordre inverse pour respecter le sens de lecture RTL.

    La comparaison au libellé tolère les erreurs d'OCR courantes sur l'écriture
    arabe via une similarité approximative plutôt qu'une égalité stricte.
    """
    for line in lines:
        words = line["words"]
        for label in label_variants:
            label_word_count = len(label.split())
            if len(words) <= label_word_count:
                continue
            tail_rtl = normalize(" ".join(reversed(words[-label_word_count:])))
            if _similar(tail_rtl, normalize(label)):
                value_words = words[:-label_word_count]
                if value_words:
                    return " ".join(reversed(value_words))
    return None


def extract_standalone_number(lines: list[Line], min_digits: int = 7, max_digits: int = 9) -> str | None:
    """Repère un numéro isolé sur sa propre ligne (ex. numéro de CIN), un motif
    fréquent sur les documents officiels indépendamment de la langue."""
    for line in lines:
        words = line["words"]
        if len(words) != 1:
            continue
        candidate = words[0]
        if candidate.isdigit() and min_digits <= len(candidate) <= max_digits:
            return candidate
    return None


def extract_value_right_of_label(
    lines: list[Line], label_variants: list[str], threshold: float = 0.75
) -> str | None:
    """Extraction positionnelle pour les formulaires en écriture latine (LTR), où
    le libellé précède sa valeur sur la même ligne (ex. tableau d'un acte de
    naissance : "PRENOMS MOUNIR"). Symétrique de extract_value_left_of_label,
    utilisée pour les documents en écriture arabe."""
    for line in lines:
        words = line["words"]
        for label in label_variants:
            label_word_count = len(label.split())
            if len(words) <= label_word_count:
                continue
            head = normalize(" ".join(words[:label_word_count]))
            if _similar(head, normalize(label), threshold):
                value_words = words[label_word_count:]
                if value_words:
                    return _strip_footnote_marks(" ".join(value_words))
    return None


def extract_value_from_adjacent_line(
    lines: list[Line], label_variants: list[str], offset: int = -1, threshold: float = 0.75
) -> str | None:
    """Repli pour les tableaux dont l'analyse de mise en page sépare un libellé de
    sa valeur sur deux lignes OCR distinctes (ex. "NOM" seul sur une ligne, la
    valeur "BARAKATI" isolée sur la ligne voisine). Ne s'applique qu'aux lignes ne
    contenant que le libellé, pour éviter de capturer la valeur d'un autre champ."""
    for i, line in enumerate(lines):
        words = line["words"]
        if len(words) > 2:
            continue
        joined = normalize(" ".join(words))
        for label in label_variants:
            if _similar(joined, normalize(label), threshold):
                neighbour_index = i + offset
                if 0 <= neighbour_index < len(lines) and lines[neighbour_index]["words"]:
                    return _strip_footnote_marks(" ".join(lines[neighbour_index]["words"]))
    return None


class BaseExtractor(ABC):
    """Interface commune de tous les extracteurs spécialisés (rapport §3.5)."""

    document_type: str = ""
    required_fields: list[str] = []

    @abstractmethod
    def _extract_fields(self, text: str, lines: list[Line] | None = None, image: np.ndarray | None = None) -> dict:
        """Extrait les champs propres au type de document depuis le texte OCR brut.

        `lines` (optionnel) fournit le même texte regroupé par ligne, mots triés
        par position horizontale, avec la boîte englobante de chaque ligne -
        nécessaire aux extracteurs positionnels (documents en écriture arabe ou
        en tableau, cf. CINExtractor, ActeNaissanceExtractor).

        `image` (optionnel) fournit l'image prétraitée elle-même, pour une
        seconde passe OCR ciblée (zoom) sur une zone trop dégradée en une seule
        passe globale (cf. ocr.tesseract_engine.zoom_ocr_text)."""

    def _build_warnings(self, text: str, fields: dict) -> list[str]:
        return []

    def extract(self, text: str, lines: list[Line] | None = None, image: np.ndarray | None = None) -> dict:
        fields = {k: v for k, v in self._extract_fields(text, lines or [], image).items() if v}
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
