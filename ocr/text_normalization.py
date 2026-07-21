"""Normalisation du texte OCR brut, utilisée par la classification et l'extraction.

L'OCR restitue de façon inégale les accents et la casse selon la qualité du scan ;
on compare donc les mots-clés sur une forme normalisée (minuscules, sans accents).
"""
import unicodedata


def normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text
