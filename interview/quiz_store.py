"""Persistance simple (fichiers JSON) reliant l'espace candidat (quiz de
pré-entretien) et l'espace enseignant (vérification des dossiers) - demandé
par l'encadrante en complément du Module 2 du rapport.

Persistance minimale par fichier, adaptée à un POC local : pas de base de
données, pas d'authentification. `candidate_key` n'est qu'une clé de
correspondance dérivée du nom complet, pas un identifiant d'authentification.

Ces fichiers contiennent des données personnelles (nom du candidat, résultats)
et ne doivent jamais être versionnés - cf. .gitignore (data/quiz_results/).
"""
import json
from datetime import datetime
from pathlib import Path

from config.settings import DATA_DIR
from ocr.text_normalization import normalize

QUIZ_RESULTS_DIR = DATA_DIR / "quiz_results"
QUIZ_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def candidate_key(nom_complet: str) -> str:
    """Dérive une clé de fichier à partir du nom complet (minuscules, sans
    accents, espaces remplacés)."""
    slug = normalize(nom_complet).strip().replace(" ", "_")
    return slug or "candidat"


def _path_for(key: str) -> Path:
    return QUIZ_RESULTS_DIR / f"{key}.json"


def _read(key: str) -> dict:
    path = _path_for(key)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write(key: str, data: dict) -> None:
    _path_for(key).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_profile(key: str, profile: dict) -> None:
    """Enregistre le profil candidat (issu de la vérification des documents),
    pour que l'espace candidat puisse générer un quiz sans ré-uploader ses
    documents."""
    data = _read(key)
    data["profile"] = profile
    data["profile_updated_at"] = datetime.now().isoformat(timespec="seconds")
    _write(key, data)


def save_quiz_result(key: str, quiz: list[dict], answers: list[int | None], score: int, total: int) -> None:
    """Enregistre le résultat du quiz de pré-entretien, consultable ensuite par
    l'enseignant dans son espace de vérification."""
    data = _read(key)
    data["quiz"] = quiz
    data["answers"] = answers
    data["score"] = score
    data["total"] = total
    data["quiz_completed_at"] = datetime.now().isoformat(timespec="seconds")
    _write(key, data)


def load(key: str) -> dict | None:
    data = _read(key)
    return data or None


def list_candidate_keys() -> list[str]:
    return sorted(p.stem for p in QUIZ_RESULTS_DIR.glob("*.json"))
