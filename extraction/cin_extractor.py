"""Extracteur pour la carte d'identité nationale (rapport §2.1)."""
import re
from difflib import SequenceMatcher

import numpy as np

from extraction.base_extractor import (
    BaseExtractor,
    extract_after_label,
    extract_standalone_number,
    extract_value_left_of_label,
)
from ocr.text_normalization import normalize
from ocr.tesseract_engine import zoom_ocr_text

# Libellés arabes imprimés sur une CIN tunisienne, avec variantes tolérant les
# erreurs de lecture courantes de l'OCR sur ce script (rapport §2.2.1, §8.3).
_ARABIC_LABELS = {
    "nom": ["اللقب"],
    "prenom": ["الاسم"],
    "date_naissance": ["تاريخ الولادة"],
    "lieu_naissance": ["مكان الولادة", "مكانها"],
    "nationalite": ["الجنسية"],
}

# Un jour à un seul chiffre isolé (bruit OCR fréquent) est ambigu : on cherche
# en priorité un jour à deux chiffres avant de se rabattre sur un seul chiffre,
# pour éviter de capturer un chiffre parasite au lieu du vrai jour.
_DATE_FRAGMENT_STRICT = re.compile(
    r"\d{2}[^\d\n]{0,20}(?:19|20)\d{2}|(?:19|20)\d{2}[^\d\n]{0,20}\d{2}", re.DOTALL
)
_DATE_FRAGMENT_LOOSE = re.compile(
    r"\d{1,2}[^\d\n]{0,20}(?:19|20)\d{2}|(?:19|20)\d{2}[^\d\n]{0,20}\d{1,2}", re.DOTALL
)
_ARABIC_WORD_PATTERN = re.compile(r"[؀-ۿ]+")


def _find_label_line_index(lines: list[dict], label_variants: list[str], threshold: float = 0.7) -> int | None:
    """Retourne l'indice de la ligne dont les derniers mots correspondent à l'un
    des libellés (même logique que extract_value_left_of_label, mais renvoie la
    position de la ligne plutôt que sa valeur - nécessaire pour recadrer l'image
    autour d'une ligne voisine)."""
    for i, line in enumerate(lines):
        words = line["words"]
        for label in label_variants:
            label_word_count = len(label.split())
            if len(words) <= label_word_count:
                continue
            tail_rtl = normalize(" ".join(reversed(words[-label_word_count:])))
            if SequenceMatcher(None, tail_rtl, normalize(label)).ratio() >= threshold:
                return i
    return None


def _extract_nom_from_line_before_prenom(lines: list[dict], prenom_index: int | None) -> str | None:
    """Repli quand le libellé "اللقب" (nom) n'est pas reconnu par l'OCR - fréquent
    en pratique, ce libellé étant imprimé en petit sur la carte.

    Sur le gabarit officiel de la CIN tunisienne, le champ nom précède toujours
    immédiatement le champ prénom : si la ligne du prénom est repérée de façon
    fiable, la ligne précédente est donc, par construction du document, celle du
    nom. On en retire le dernier mot (le libellé du nom, même mal reconnu) pour
    ne garder que sa valeur.
    """
    if not prenom_index or prenom_index == 0:
        return None
    previous_words = lines[prenom_index - 1]["words"]
    if len(previous_words) >= 2:
        return " ".join(reversed(previous_words[:-1]))
    return None


def _best_arabic_token(text: str, min_length: int = 3) -> str | None:
    """Retient, dans un texte OCR, le mot en écriture arabe le plus long - une
    seconde passe OCR ciblée (zoom) mélange souvent la valeur avec des débris du
    libellé voisin ; le mot le plus long est en pratique presque toujours la
    valeur recherchée plutôt qu'un fragment de libellé tronqué."""
    candidates = [w for w in _ARABIC_WORD_PATTERN.findall(text) if len(w) >= min_length]
    if not candidates:
        return None
    return max(candidates, key=len)


def _find_date_like_fragment(text: str) -> str | None:
    """Repère un fragment "jour ... année" (ex. "12 اوت 2003") dans un texte OCR,
    sans tenter de reconstruire une date propre : le mois, souvent mal reconnu,
    est conservé tel quel plutôt que d'être deviné, pour rester honnête sur ce
    que l'OCR a effectivement lu."""
    match = _DATE_FRAGMENT_STRICT.search(text) or _DATE_FRAGMENT_LOOSE.search(text)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(0)).strip()


class CINExtractor(BaseExtractor):
    document_type = "cin"
    required_fields = ["nom", "prenom", "date_naissance", "numero_document"]

    def _extract_fields(self, text: str, lines: list[dict] | None = None, image: np.ndarray | None = None) -> dict:
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

            prenom_index = _find_label_line_index(lines, _ARABIC_LABELS["prenom"])

            # 3) Dernier repli pour "nom" : le libellé "اللقب" est rarement bien
            # reconnu par l'OCR (police décorative, petite taille) - on se rabat sur
            # sa position connue, juste avant la ligne du prénom.
            if not fields.get("nom"):
                value = _extract_nom_from_line_before_prenom(lines, prenom_index)
                if value:
                    fields["nom"] = value
                    self._fields_from_positional_fallback.add("nom")

            # 4) Seconde passe OCR ciblée (zoom) : le texte est souvent trop petit
            # ou noyé dans le fond décoratif de la carte pour être lu correctement
            # en une seule passe globale. On isole puis agrandit les zones d'intérêt
            # une fois leur position connue (ligne du prénom, fiable) - vérifié
            # empiriquement sur une vraie CIN tunisienne.
            if image is not None and prenom_index is not None:
                prenom_line = lines[prenom_index]

                if prenom_index > 0:
                    nom_line = lines[prenom_index - 1]
                    # psm 7 (une seule ligne de texte) donne, empiriquement, une
                    # bien meilleure reconnaissance qu'un mode de segmentation
                    # multi-lignes sur une bande aussi étroite ; on recadre sur
                    # toute la largeur de l'image car la boîte englobante fournie
                    # par l'OCR (basée sur une lecture déjà erronée) ne couvre pas
                    # forcément l'étendue réelle du mot.
                    zoomed_nom_text = zoom_ocr_text(
                        image,
                        top=nom_line["top"] - 20,
                        bottom=nom_line["bottom"] + 20,
                        left=0,
                        right=None,
                        psm=7,
                    )
                    better_nom = _best_arabic_token(zoomed_nom_text)
                    if better_nom and len(better_nom) > len(fields.get("nom") or ""):
                        fields["nom"] = better_nom
                        self._fields_from_positional_fallback.add("nom")

                if not fields.get("date_naissance"):
                    line_height = prenom_line["bottom"] - prenom_line["top"]
                    # Une bande trop haute capture aussi le début du verso de la
                    # carte et brouille la segmentation ; ~3 lignes de champ
                    # suffisent à couvrir la ligne de la date de naissance.
                    band_bottom = prenom_line["bottom"] + line_height * 3
                    for psm in (6, 4, 11):
                        zoomed_band_text = zoom_ocr_text(
                            image, top=prenom_line["bottom"] + 10, bottom=band_bottom, psm=psm
                        )
                        date_fragment = _find_date_like_fragment(zoomed_band_text)
                        if date_fragment:
                            fields["date_naissance"] = date_fragment
                            self._fields_from_positional_fallback.add("date_naissance")
                            break

        return fields

    def _build_warnings(self, text: str, fields: dict) -> list[str]:
        estimated = getattr(self, "_fields_from_positional_fallback", set())
        if not estimated:
            return []
        champs = ", ".join(sorted(estimated))
        return [f"champs_estimes_par_position_carte_arabe: {champs}"]
