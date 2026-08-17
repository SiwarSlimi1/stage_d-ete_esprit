"""Évalue le pipeline réel (prétraitement -> OCR -> classification -> extraction
-> vérifications de cohérence) sur le jeu de données à grande échelle généré par
tests/generate_dataset_images.py (data/samples_dataset/, 1000 dossiers avec
vérité terrain dans manifest.jsonl).

Comble un manque identifié au rapport (§7, §9, §10) : les 38 tests unitaires ne
portent que sur un seul candidat synthétique ("BEN ALI SALMA"), ce qui suffit à
valider que le pipeline tourne mais pas à mesurer sa fiabilité réelle ni sa
capacité (actuelle et future) à détecter les anomalies d'un dossier. Ce script
fait tourner le pipeline sur un échantillon (ou l'intégralité) du dataset et
mesure, par type de document et par type d'anomalie :
  - la précision de classification (document_type détecté vs attendu) ;
  - le statut d'extraction (success/partial/failed) ;
  - l'exactitude champ par champ par rapport à la vérité terrain ;
  - le taux de détection de verification.identity_checker (nom/prénom,
    y compris une inversion nom/prénom) ;
  - le taux de détection de verification.academic_years_checker (doublons,
    années manquantes, erreurs de classement, cohérence avec la licence) ;
  - le taux de faux positifs de verification.duplicate_document_checker (le
    dataset ne contient pas de scénario "document dupliqué" au sens propre -
    utile ici pour vérifier qu'il ne se déclenche jamais par erreur entre des
    relevés d'années différentes qui se ressemblent structurellement).

Usage :
    python -m tests.evaluate_pipeline --per-anomalie 15   # ~105 dossiers (defaut)
    python -m tests.evaluate_pipeline --full               # les 1000 dossiers (long)
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from classification.rules_classifier import DocumentClassifier
from config.settings import DATA_DIR, REPORTS_DIR
from extraction import get_extractor
from models.candidate_file import Document
from ocr.text_normalization import normalize
from verification.academic_years_checker import check_academic_years
from verification.duplicate_document_checker import check_duplicate_documents
from verification.identity_checker import check_identity_consistency

DATASET_DIR = DATA_DIR / "samples_dataset"
_classifier = DocumentClassifier()

# {champ_extrait: champ_verite_terrain} par type de document (rapport §3.2.4 /
# §2.1 pour les champs extraits ; contrat du générateur pour la vérité terrain).
FIELD_MAP = {
    "cin": {"nom": "nom", "prenom": "prenom", "date_naissance": "date_naissance",
            "lieu_naissance": "lieu_naissance", "numero_document": "numero_document"},
    "acte_naissance": {"nom": "nom", "prenom": "prenom", "date_naissance": "date_naissance",
                        "lieu_naissance": "lieu_naissance"},
    "bac": {"nom": "nom", "prenom": "prenom", "annee_obtention": "annee_obtention",
            "filiere_bac": "serie", "mention": "mention"},
    "diplome_licence": {"nom": "nom", "prenom": "prenom", "specialite": "specialite",
                         "annee_obtention": "annee_obtention", "etablissement": "etablissement"},
    "releve_notes": {"annee_universitaire": "annee_universitaire", "moyenne": "moyenne"},
}

# Anomalies censées être détectées par chaque module (taux de détection bas
# attendu = "consistent" bas) vs les autres, où seul un faux positif proche de
# zéro est attendu ("consistent" haut).
IDENTITY_ANOMALIES = {"nom_mal_orthographie", "identite_releve_inversee"}
ACADEMIC_YEARS_ANOMALIES = {"annee_universitaire_dupliquee", "annee_licence_incoherente"}


def process_document_with_text(path: Path) -> tuple[dict, str]:
    """Réplique main.process_document mais retourne aussi le texte OCR brut
    (nécessaire à la détection de documents dupliqués), pour éviter de lancer
    l'OCR une seconde fois sur chaque document."""
    document = Document(image_path=str(path))
    document.run_ocr(document.preprocess())

    classification = _classifier.classify_with_confidence(document.raw_text)
    document.doc_type = classification["document_type"]
    document.classification_confidence = classification["confidence"]

    extractor = get_extractor(document.doc_type)
    if extractor is None:
        result = {
            "document_type": document.doc_type, "fields": {}, "missing_fields": [],
            "warnings": ["type_de_document_non_reconnu"], "extraction_status": "failed",
        }
    else:
        result = extractor.extract(document.raw_text, document.word_lines, document.processed_image)
    result["classification_confidence"] = document.classification_confidence
    result["source_image"] = str(path)
    return result, document.raw_text


def _values_match(extracted, ground_truth) -> bool:
    if extracted is None or ground_truth is None:
        return False
    if isinstance(ground_truth, float):
        ground_truth = f"{ground_truth:.2f}"
    return normalize(str(extracted)).strip() == normalize(str(ground_truth)).strip()


def _releve_ground_truth(ground_truth: dict, niveau: str) -> dict | None:
    for releve in ground_truth.get("releve_notes", []):
        if releve.get("niveau") == niveau:
            return releve
    return None


def _compare_fields(doc_key: str, result: dict, ground_truth: dict) -> tuple[int, int]:
    """Retourne (nb_champs_corrects, nb_champs_compares) pour un document."""
    fields = result["fields"]

    if doc_key.startswith("releve_"):
        niveau = doc_key.removeprefix("releve_")
        gt = _releve_ground_truth(ground_truth, niveau)
        if gt is None:
            return 0, 0
        field_map = FIELD_MAP["releve_notes"]
    else:
        gt = ground_truth.get(doc_key)
        if gt is None:
            return 0, 0
        field_map = FIELD_MAP.get(doc_key, {})

    correct = sum(1 for extracted_key, gt_key in field_map.items() if _values_match(fields.get(extracted_key), gt.get(gt_key)))
    total = len(field_map)

    if doc_key == "acte_naissance":
        total += 1
        filiation = normalize(str(fields.get("filiation") or ""))
        if normalize(str(gt.get("nom_pere") or "")) in filiation and normalize(str(gt.get("nom_mere") or ""))  in filiation:
            correct += 1

    return correct, total


def _expected_type(doc_key: str) -> str:
    return "releve_notes" if doc_key.startswith("releve_") else doc_key


def load_manifest(limit_per_anomalie: int | None) -> list[dict]:
    manifest_path = DATASET_DIR / "manifest.jsonl"
    with open(manifest_path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]

    if limit_per_anomalie is None:
        return entries

    by_anomalie: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        by_anomalie[entry["anomalie"]].append(entry)

    sampled = []
    for anomalie, group in sorted(by_anomalie.items()):
        sampled.extend(group[:limit_per_anomalie])
    return sampled


def evaluate(entries: list[dict]) -> dict:
    by_doc_type = defaultdict(lambda: {"classification_correct": 0, "total": 0, "status": defaultdict(int),
                                        "fields_correct": 0, "fields_total": 0})
    by_anomalie = defaultdict(lambda: {
        "nb_dossiers": 0,
        "identity_consistent": 0, "identity_comparable": 0,
        "academic_years_consistent": 0,
        "duplicate_consistent": 0,
    })
    details = []

    for i, entry in enumerate(entries):
        dossier_dir = DATASET_DIR / entry["dossier_dir"]
        ground_truth = entry["ground_truth"]
        anomalie = entry["anomalie"]
        by_anomalie[anomalie]["nb_dossiers"] += 1

        identity_documents, raw_text_documents, releve_fields = [], [], []
        licence_fields = None
        dossier_detail = {"dossier_dir": entry["dossier_dir"], "anomalie": anomalie, "documents": {}}

        for doc_key, filename in entry["fichiers_generes"].items():
            path = dossier_dir / filename
            result, raw_text = process_document_with_text(path)
            expected_type = _expected_type(doc_key)

            stats = by_doc_type[expected_type]
            stats["total"] += 1
            stats["status"][result["extraction_status"]] += 1
            if result["document_type"] == expected_type:
                stats["classification_correct"] += 1

            correct, total = _compare_fields(doc_key, result, ground_truth)
            stats["fields_correct"] += correct
            stats["fields_total"] += total

            identity_documents.append({"label": doc_key, "fields": result["fields"]})
            raw_text_documents.append({"label": doc_key, "raw_text": raw_text})
            if expected_type == "releve_notes":
                releve_fields.append(result["fields"])
            elif expected_type == "diplome_licence":
                licence_fields = result["fields"]

            dossier_detail["documents"][doc_key] = {
                "document_type": result["document_type"],
                "extraction_status": result["extraction_status"],
                "fields_correct": correct,
                "fields_total": total,
            }

        identity_result = check_identity_consistency(identity_documents)
        if identity_result["comparable_documents"] >= 2:
            by_anomalie[anomalie]["identity_comparable"] += 1
            if identity_result["consistent"]:
                by_anomalie[anomalie]["identity_consistent"] += 1

        academic_years_result = check_academic_years(releve_fields, licence_fields)
        if academic_years_result["consistent"]:
            by_anomalie[anomalie]["academic_years_consistent"] += 1

        duplicate_result = check_duplicate_documents(raw_text_documents)
        if duplicate_result["consistent"]:
            by_anomalie[anomalie]["duplicate_consistent"] += 1

        dossier_detail["identity_consistent"] = identity_result["consistent"]
        dossier_detail["academic_years_consistent"] = academic_years_result["consistent"]
        dossier_detail["academic_years_issues"] = academic_years_result["issues"]
        dossier_detail["duplicate_consistent"] = duplicate_result["consistent"]
        details.append(dossier_detail)

        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(entries)} dossiers traites...")

    return {"by_doc_type": by_doc_type, "by_anomalie": by_anomalie, "details": details}


def print_report(results: dict, nb_dossiers: int) -> None:
    print(f"\n=== Classification et extraction ({nb_dossiers} dossiers) ===")
    print(f"{'type':<18}{'classif.':>10}{'success':>10}{'partial':>10}{'failed':>10}{'champs OK':>12}")
    for doc_type, stats in sorted(results["by_doc_type"].items()):
        classif_pct = 100 * stats["classification_correct"] / stats["total"]
        fields_pct = 100 * stats["fields_correct"] / stats["fields_total"] if stats["fields_total"] else 0
        print(
            f"{doc_type:<18}{classif_pct:>9.1f}%{stats['status']['success']:>10}"
            f"{stats['status']['partial']:>10}{stats['status']['failed']:>10}{fields_pct:>11.1f}%"
        )

    print(f"\n=== Cohérence par type d'anomalie ===")
    print(f"{'anomalie':<38}{'dossiers':>9}{'identite':>10}{'annees':>9}{'doublons':>10}")
    for anomalie, stats in sorted(results["by_anomalie"].items()):
        comparable = stats["identity_comparable"]
        identity_pct = 100 * stats["identity_consistent"] / comparable if comparable else float("nan")
        academic_pct = 100 * stats["academic_years_consistent"] / stats["nb_dossiers"]
        duplicate_pct = 100 * stats["duplicate_consistent"] / stats["nb_dossiers"]
        print(f"{anomalie:<38}{stats['nb_dossiers']:>9}{identity_pct:>9.1f}%{academic_pct:>8.1f}%{duplicate_pct:>9.1f}%")

    print(
        "\n(colonnes = % de dossiers jugés 'coherent' par chaque module ; bas attendu sur "
        f"{sorted(IDENTITY_ANOMALIES)} pour 'identite', sur {sorted(ACADEMIC_YEARS_ANOMALIES)} pour 'annees' ; "
        "~100% attendu partout ailleurs, et sur 'doublons' pour toutes les categories - "
        "ce dataset ne contient pas de scenario document-duplique au sens propre)"
    )


def _json_default(obj):
    if isinstance(obj, defaultdict):
        return dict(obj)
    raise TypeError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-anomalie", type=int, default=15, help="Dossiers par type d'anomalie (defaut: 15)")
    parser.add_argument("--full", action="store_true", help="Traiter les 1000 dossiers")
    args = parser.parse_args()

    entries = load_manifest(None if args.full else args.per_anomalie)
    print(f"Evaluation sur {len(entries)} dossiers...")
    results = evaluate(entries)
    print_report(results, len(entries))

    report_path = REPORTS_DIR / f"evaluation_pipeline_{datetime.now():%Y%m%d_%H%M%S}.json"
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    print(f"\nDetail complet ecrit dans : {report_path}")


if __name__ == "__main__":
    main()
