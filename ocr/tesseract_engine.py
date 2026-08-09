"""Interface avec le moteur OCR Tesseract (rapport §3.2.2)."""
import cv2
import numpy as np
import pytesseract
from pytesseract import Output

from config.settings import OCR_LANGUAGES, TESSERACT_CMD

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def extract_text(image: np.ndarray, lang: str = OCR_LANGUAGES) -> str:
    """Extrait le texte brut d'une image déjà prétraitée."""
    return pytesseract.image_to_string(image, lang=lang)


def extract_text_with_confidence(image: np.ndarray, lang: str = OCR_LANGUAGES) -> dict:
    """Extrait le texte ainsi que les scores de confiance par mot (rapport §3.2.2).

    Retourne : {"text": str, "mean_confidence": float, "words": [{"text": str, "confidence": float}, ...]}
    """
    data = pytesseract.image_to_data(image, lang=lang, output_type=Output.DICT)

    words = []
    confidences = []
    for text, conf in zip(data["text"], data["conf"]):
        text = text.strip()
        conf = float(conf)
        if not text or conf < 0:
            continue
        words.append({"text": text, "confidence": conf})
        confidences.append(conf)

    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    full_text = " ".join(w["text"] for w in words)

    return {
        "text": full_text,
        "mean_confidence": round(mean_confidence, 2),
        "words": words,
    }


def extract_lines(image: np.ndarray, lang: str = OCR_LANGUAGES, psm: int = 4) -> list[dict]:
    """Retourne le texte OCR regroupé par ligne, chaque ligne apportant à la fois
    ses mots (triés de gauche à droite, coordonnées image) et sa boîte englobante
    ({"words": [...], "top": int, "bottom": int, "left": int, "right": int}).

    Utilisé pour l'extraction positionnelle sur les documents en écriture arabe
    (RTL), où le libellé d'un champ est imprimé à droite de la valeur sur la même
    ligne : le texte brut linéaire (extract_text) ne permet pas de retrouver cette
    relation, alors que les coordonnées des mots le permettent. La boîte englobante
    permet en complément de recadrer et zoomer sur une ligne précise pour une
    seconde passe OCR ciblée (cf. zoom_ocr_text) quand le texte y est trop dégradé.
    """
    data = pytesseract.image_to_data(image, lang=lang, config=f"--psm {psm}", output_type=Output.DICT)

    grouped: dict[tuple, list[dict]] = {}
    for i, text in enumerate(data["text"]):
        text = text.strip()
        if not text or float(data["conf"][i]) < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        left, top, width, height = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        grouped.setdefault(key, []).append(
            {"left": left, "top": top, "right": left + width, "bottom": top + height, "text": text}
        )

    lines = []
    for key in sorted(grouped.keys()):
        entries = sorted(grouped[key], key=lambda e: e["left"])
        lines.append(
            {
                "words": [e["text"] for e in entries],
                "top": min(e["top"] for e in entries),
                "bottom": max(e["bottom"] for e in entries),
                "left": min(e["left"] for e in entries),
                "right": max(e["right"] for e in entries),
            }
        )
    return lines


def zoom_ocr_text(
    image: np.ndarray,
    top: int,
    bottom: int,
    left: int = 0,
    right: int | None = None,
    scale: float = 2.5,
    psm: int = 11,
    lang: str = OCR_LANGUAGES,
) -> str:
    """Ré-OCRise une zone précise de l'image, recadrée puis agrandie.

    Sur une carte d'identité, le texte est souvent trop petit ou noyé dans un
    fond décoratif pour être lu correctement en une seule passe sur l'image
    entière ; isoler puis agrandir la zone d'intérêt améliore nettement la
    reconnaissance (vérifié empiriquement sur une vraie CIN tunisienne).
    """
    height, width = image.shape[:2]
    top, bottom = max(0, top), min(height, bottom)
    right = width if right is None else min(width, right)
    band = image[top:bottom, left:right]
    if band.size == 0:
        return ""
    upscaled = cv2.resize(band, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return pytesseract.image_to_string(upscaled, lang=lang, config=f"--psm {psm}")
