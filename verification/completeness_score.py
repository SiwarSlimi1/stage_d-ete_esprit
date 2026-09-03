"""Score de complétude global du dossier (rapport §9, §10) : synthèse chiffrée
combinant les signaux déjà disponibles du pipeline - présence des documents
attendus du dossier, complétude de l'extraction des champs, et résultat des 3
vérifications de cohérence (identity_checker, academic_years_checker,
duplicate_document_checker) - en une seule note et un statut, pour aider les
enseignants à prioriser les dossiers à examiner en détail.

Le barème ci-dessous (pondération, config/settings.py) est une valeur par
défaut du POC, documentée et ajustable : l'encadrante n'a pas fourni de barème
officiel à ce jour (rapport §10). Le niveau académique (moyennes minimales,
mentions attendues) reste volontairement hors périmètre de ce score : aucun
critère d'admission n'a été défini (cf. data/dossiers_synthetiques/README.md,
scénario "echec_annee").

Comme les autres modules de verification/, ce score n'est qu'un indicateur
d'aide à la décision : il ne rejette ni n'admet jamais un dossier (rapport
§1.5).
"""
from config.settings import (
    COMPLETENESS_WEIGHT_COHERENCE,
    COMPLETENESS_WEIGHT_EXTRACTION,
    COMPLETENESS_WEIGHT_PRESENCE,
)


def _extraction_completeness(filled_results: list[dict]) -> float:
    """Moyenne, sur les documents fournis, de la part de champs effectivement
    extraits (champs extraits / (champs extraits + champs manquants)). Un
    document sans aucun champ attendu (ex. type non reconnu) compte pour 0 -
    déjà pénalisé par ailleurs via extraction_status: "failed"."""
    if not filled_results:
        return 1.0  # rien à extraire : ne doit pas pénaliser en plus de la présence

    ratios = []
    for item in filled_results:
        fields, missing = item["result"]["fields"], item["result"]["missing_fields"]
        total = len(fields) + len(missing)
        ratios.append(len(fields) / total if total else 0.0)
    return sum(ratios) / len(ratios)


def compute_completeness(
    active_slots: list[dict],
    filled_results: list[dict],
    identity_result: dict,
    academic_years_result: dict,
    duplicate_result: dict,
) -> dict:
    """Calcule le score de complétude global d'un dossier.

    `active_slots` / `filled_results` : mêmes structures que dans app.py - un
    slot par document attendu du dossier (`{"label": str, ...}`) ;
    `filled_results` ne contient que les slots effectivement renseignés,
    chacun sous la forme `{"slot": <slot de active_slots>, "result": {...}}`
    (comparaison par identité d'objet, pas par libellé, pour rester correcte
    même si deux slots partagent un libellé).

    Retourne :
    {
      "score": float,              # 0.0 - 1.0
      "status": str,                # "documents_manquants" | "anomalie_detectee"
                                     # | "extraction_incomplete" | "complet"
      "presence_score": float,
      "extraction_score": float,
      "coherence_score": float,
      "missing_documents": [str, ...],  # libellés des slots non renseignés
    }
    """
    nb_total = len(active_slots)
    presence_score = len(filled_results) / nb_total if nb_total else 1.0

    filled_slot_ids = {id(item["slot"]) for item in filled_results}
    missing_documents = [slot["label"] for slot in active_slots if id(slot) not in filled_slot_ids]

    extraction_score = _extraction_completeness(filled_results)

    checks = (identity_result["consistent"], academic_years_result["consistent"], duplicate_result["consistent"])
    coherence_score = sum(checks) / len(checks)

    if presence_score == 0.0:
        # Dossier entièrement vide (documents attendus mais aucun fourni) :
        # extraction et cohérence n'ont rien à évaluer et ne doivent pas
        # produire de score plancher trompeur, contrairement au cas où aucun
        # document n'est attendu (nb_total == 0), où presence_score vaut 1.0
        # et non 0.0 - ces deux scores restent donc cohérents avec le score
        # global plutôt que d'être laissés à leur valeur par défaut (1.0) alors
        # que celui-ci affiche 0%.
        extraction_score = 0.0
        coherence_score = 0.0

    score = (
        COMPLETENESS_WEIGHT_PRESENCE * presence_score
        + COMPLETENESS_WEIGHT_EXTRACTION * extraction_score
        + COMPLETENESS_WEIGHT_COHERENCE * coherence_score
    )

    # Ordre de priorité du statut : un document manquant prime sur une
    # anomalie de cohérence, elle-même plus parlante qu'une extraction
    # partielle (un champ isolé mal reconnu par l'OCR).
    if presence_score < 1.0:
        status = "documents_manquants"
    elif coherence_score < 1.0:
        status = "anomalie_detectee"
    elif extraction_score < 1.0:
        status = "extraction_incomplete"
    else:
        status = "complet"

    return {
        "score": score,
        "status": status,
        "presence_score": presence_score,
        "extraction_score": extraction_score,
        "coherence_score": coherence_score,
        "missing_documents": missing_documents,
    }
