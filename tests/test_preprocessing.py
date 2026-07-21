"""Tests unitaires du module de prétraitement OpenCV (rapport §7.1)."""
import cv2
import numpy as np
import pytest

from preprocessing.deskew import compute_skew_angle, deskew
from preprocessing.image_utils import (
    binarize,
    denoise,
    load_image,
    preprocess_pipeline,
    resize_for_ocr,
    to_grayscale,
)


def _make_skewed_block(angle_deg: float) -> np.ndarray:
    image = np.full((300, 300), 255, dtype=np.uint8)
    cv2.rectangle(image, (50, 140), (250, 160), 0, -1)
    matrix = cv2.getRotationMatrix2D((150, 150), angle_deg, 1.0)
    return cv2.warpAffine(image, matrix, (300, 300), borderValue=255)


def test_load_image_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_image("data/samples/ne_existe_pas.png")


def test_to_grayscale_reduces_to_single_channel():
    color_image = np.zeros((50, 50, 3), dtype=np.uint8)
    gray = to_grayscale(color_image)
    assert gray.ndim == 2


def test_resize_for_ocr_reaches_target_width():
    gray = np.zeros((100, 300), dtype=np.uint8)
    resized = resize_for_ocr(gray, target_width=600)
    assert resized.shape[1] == 600


def test_denoise_preserves_shape():
    gray = np.random.randint(0, 255, (80, 80), dtype=np.uint8)
    assert denoise(gray).shape == gray.shape


def test_binarize_produces_only_black_and_white():
    gray = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    binary = binarize(gray)
    assert set(np.unique(binary)).issubset({0, 255})


def test_deskew_reduces_measured_skew_angle():
    skewed = _make_skewed_block(10)
    angle_before = compute_skew_angle(skewed)
    corrected = deskew(skewed)
    angle_after = compute_skew_angle(corrected)
    assert abs(angle_after) < abs(angle_before)


def test_preprocess_pipeline_on_real_sample(sample_documents):
    image = load_image(sample_documents["cin"])
    processed = preprocess_pipeline(image)
    assert processed.ndim == 2
    assert set(np.unique(processed)).issubset({0, 255})
