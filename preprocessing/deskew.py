"""Correction d'inclinaison (deskew) d'une image de document scanné, cf. rapport §3.2.1."""
import cv2
import numpy as np

MAX_CORRECTABLE_ANGLE = 15.0  # au-delà, on suppose une erreur de mesure et on n'y touche pas
MIN_FOREGROUND_PIXELS = 20  # image quasi vide -> pas de mesure fiable possible


def _normalize_angle(angle: float) -> float:
    """Ramène un angle de rectangle OpenCV dans l'intervalle (-45, 45]."""
    angle = angle % 90
    if angle > 45:
        angle -= 90
    return angle


def compute_skew_angle(gray_image: np.ndarray) -> float:
    """Estime l'angle d'inclinaison (en degrés) du texte dans l'image."""
    _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    if coords.shape[0] < MIN_FOREGROUND_PIXELS:
        return 0.0
    rect_angle = cv2.minAreaRect(coords)[-1]
    return _normalize_angle(rect_angle)


def deskew(gray_image: np.ndarray) -> np.ndarray:
    """Corrige l'inclinaison de l'image si elle est mesurable et plausible."""
    angle = compute_skew_angle(gray_image)
    if abs(angle) < 0.1 or abs(angle) > MAX_CORRECTABLE_ANGLE:
        return gray_image
    height, width = gray_image.shape[:2]
    center = (width // 2, height // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
    return cv2.warpAffine(
        gray_image,
        rotation_matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
