"""Interface avec le moteur OCR Tesseract (rapport §3.2.2)."""
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


def extract_lines(image: np.ndarray, lang: str = OCR_LANGUAGES, psm: int = 4) -> list[list[str]]:
    """Retourne le texte OCR regroupé par ligne, chaque ligne étant la liste de ses
    mots triés de gauche à droite (coordonnées image).

    Utilisé pour l'extraction positionnelle sur les documents en écriture arabe
    (RTL), où le libellé d'un champ est imprimé à droite de la valeur sur la même
    ligne : le texte brut linéaire (extract_text) ne permet pas de retrouver cette
    relation, alors que les coordonnées des mots le permettent.
    """
    data = pytesseract.image_to_data(image, lang=lang, config=f"--psm {psm}", output_type=Output.DICT)

    grouped: dict[tuple, list[tuple[int, str]]] = {}
    for i, text in enumerate(data["text"]):
        text = text.strip()
        if not text or float(data["conf"][i]) < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        grouped.setdefault(key, []).append((data["left"][i], text))

    lines = []
    for key in sorted(grouped.keys()):
        words = [word for _, word in sorted(grouped[key], key=lambda w: w[0])]
        lines.append(words)
    return lines
