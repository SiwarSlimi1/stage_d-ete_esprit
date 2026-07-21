"""Prétraitement OpenCV des images de documents (rapport §3.2.1).

Toutes les fonctions sont des transformations algorithmiques déterministes
(pas d'apprentissage à partir de données) : deux images similaires produisent
systématiquement le même résultat.
"""
from pathlib import Path

import cv2
import numpy as np

from config.settings import OCR_TARGET_WIDTH


def load_image(image_path: str | Path) -> np.ndarray:
    """Charge une image depuis le disque (BGR)."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image introuvable : {path}")
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Impossible de décoder l'image : {path}")
    return image


def to_grayscale(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def equalize_contrast(gray_image: np.ndarray) -> np.ndarray:
    """Égalisation d'histogramme pour compenser un scan sous/surexposé."""
    return cv2.equalizeHist(gray_image)


def adjust_gamma(gray_image: np.ndarray, gamma: float = 1.0) -> np.ndarray:
    """Correction gamma (gamma < 1 éclaircit, gamma > 1 assombrit)."""
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)], dtype="uint8")
    return cv2.LUT(gray_image, table)


def denoise(gray_image: np.ndarray) -> np.ndarray:
    """Réduction de bruit par filtre médian (atténue les artefacts de scan/JPEG)."""
    return cv2.medianBlur(gray_image, 3)


def resize_for_ocr(gray_image: np.ndarray, target_width: int = OCR_TARGET_WIDTH) -> np.ndarray:
    """Redimensionne à une largeur cible optimale pour l'OCR, sans déformer l'image."""
    height, width = gray_image.shape[:2]
    if width == 0:
        return gray_image
    scale = target_width / float(width)
    if abs(scale - 1.0) < 0.01:
        return gray_image
    interpolation = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    new_size = (target_width, max(1, int(height * scale)))
    return cv2.resize(gray_image, new_size, interpolation=interpolation)


def binarize(gray_image: np.ndarray) -> np.ndarray:
    """Binarisation par seuillage d'Otsu (texte noir sur fond blanc)."""
    _, binary = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def crop_to_content(gray_image: np.ndarray, margin: int = 15) -> np.ndarray:
    """Recadre l'image sur la zone contenant du texte/contenu (retire les bords vides)."""
    _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return gray_image
    x, y, w, h = cv2.boundingRect(coords)
    height, width = gray_image.shape[:2]
    x0, y0 = max(0, x - margin), max(0, y - margin)
    x1, y1 = min(width, x + w + margin), min(height, y + h + margin)
    return gray_image[y0:y1, x0:x1]


def preprocess_pipeline(image: np.ndarray) -> np.ndarray:
    """Chaîne complète de prétraitement avant OCR (contraste -> bruit -> deskew ->
    recadrage -> redimensionnement -> binarisation), cf. rapport §3.2.1."""
    from preprocessing.deskew import deskew  # import local pour éviter le cycle

    gray = to_grayscale(image)
    gray = equalize_contrast(gray)
    gray = denoise(gray)
    gray = deskew(gray)
    gray = crop_to_content(gray)
    gray = resize_for_ocr(gray)
    return binarize(gray)
