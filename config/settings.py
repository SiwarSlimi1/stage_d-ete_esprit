"""Paramètres globaux du POC (chemins, langues OCR, seuils)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SAMPLES_DIR = DATA_DIR / "samples"
REPORTS_DIR = DATA_DIR / "reports"
# Dossiers candidats fictifs (tests/generate_synthetic_dataset.py), utilisés par
# l'espace enseignant pour démontrer le pipeline sans données réelles (rapport §10).
SYNTHETIC_DATASET_DIR = DATA_DIR / "dossiers_synthetiques"

# Langues Tesseract activées : français, arabe, anglais (cf. rapport §3.2.2)
OCR_LANGUAGES = "fra+ara+eng"

# Chemin vers l'exécutable Tesseract. Surchageable via la variable d'environnement
# TESSERACT_CMD si le binaire n'est pas dans le PATH.
_DEFAULT_WINDOWS_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = os.environ.get("TESSERACT_CMD") or (
    _DEFAULT_WINDOWS_TESSERACT if Path(_DEFAULT_WINDOWS_TESSERACT).exists() else None
)

# Prétraitement (OpenCV)
OCR_TARGET_WIDTH = 1800  # largeur cible avant OCR (cf. rapport §3.2.1)
DENOISE_KERNEL_SIZE = 3

# Classification par règles
MIN_CLASSIFICATION_CONFIDENCE = 0.15  # sous ce seuil -> document_type = "inconnu"

# Score de complétude du dossier (verification/completeness_score.py) : barème
# par défaut du POC, pondérant présence des documents, complétude de
# l'extraction, et résultat des vérifications de cohérence - somme = 1.0.
# Aucun barème officiel n'a été fourni par l'encadrante à ce jour (rapport
# §10) ; ces valeurs sont ajustables sans changer le code.
COMPLETENESS_WEIGHT_PRESENCE = 0.5
COMPLETENESS_WEIGHT_EXTRACTION = 0.3
COMPLETENESS_WEIGHT_COHERENCE = 0.2

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
