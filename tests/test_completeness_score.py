"""Tests du score de complétude global du dossier (rapport §9, §10)."""
from verification.completeness_score import compute_completeness

CONSISTENT = {"consistent": True}
INCONSISTENT = {"consistent": False}


def _slot(label: str) -> dict:
    return {"label": label}


def _filled(slot: dict, fields: dict, missing: list | None = None) -> dict:
    return {"slot": slot, "result": {"fields": fields, "missing_fields": missing or []}}


def test_complete_dossier_with_no_anomaly_scores_full():
    cin, bac = _slot("CIN"), _slot("Bac")
    active_slots = [cin, bac]
    filled_results = [_filled(cin, {"nom": "BEN ALI"}), _filled(bac, {"annee_obtention": "2020"})]

    result = compute_completeness(active_slots, filled_results, CONSISTENT, CONSISTENT, CONSISTENT)

    assert result["score"] == 1.0
    assert result["status"] == "complet"
    assert result["missing_documents"] == []


def test_missing_document_is_reported_and_takes_priority():
    cin, bac = _slot("CIN"), _slot("Diplôme du baccalauréat")
    active_slots = [cin, bac]
    filled_results = [_filled(cin, {"nom": "BEN ALI"})]

    result = compute_completeness(active_slots, filled_results, CONSISTENT, CONSISTENT, INCONSISTENT)

    assert result["status"] == "documents_manquants"
    assert result["missing_documents"] == ["Diplôme du baccalauréat"]
    assert result["presence_score"] == 0.5
    assert result["score"] < 1.0


def test_coherence_anomaly_sets_status_even_when_dossier_complete():
    cin = _slot("CIN")
    active_slots = [cin]
    filled_results = [_filled(cin, {"nom": "BEN ALI"})]

    result = compute_completeness(active_slots, filled_results, INCONSISTENT, CONSISTENT, CONSISTENT)

    assert result["presence_score"] == 1.0
    assert result["status"] == "anomalie_detectee"
    assert result["coherence_score"] == 2 / 3


def test_partial_extraction_lowers_score_without_missing_document():
    cin = _slot("CIN")
    active_slots = [cin]
    filled_results = [_filled(cin, {"nom": "BEN ALI"}, missing=["prenom"])]

    result = compute_completeness(active_slots, filled_results, CONSISTENT, CONSISTENT, CONSISTENT)

    assert result["status"] == "extraction_incomplete"
    assert result["extraction_score"] == 0.5
    assert result["missing_documents"] == []


def test_unrecognized_document_with_no_expected_field_counts_as_zero_extraction():
    cin = _slot("CIN")
    active_slots = [cin]
    filled_results = [_filled(cin, {}, missing=[])]

    result = compute_completeness(active_slots, filled_results, CONSISTENT, CONSISTENT, CONSISTENT)

    assert result["extraction_score"] == 0.0


def test_empty_dossier_has_zero_presence_and_extraction_not_penalized_twice():
    active_slots = [_slot("CIN"), _slot("Bac")]

    result = compute_completeness(active_slots, [], CONSISTENT, CONSISTENT, CONSISTENT)

    assert result["presence_score"] == 0.0
    assert result["extraction_score"] == 1.0  # rien à extraire, déjà couvert par presence_score
    assert result["status"] == "documents_manquants"
    assert set(result["missing_documents"]) == {"CIN", "Bac"}


def test_no_active_slots_defaults_to_full_presence():
    result = compute_completeness([], [], CONSISTENT, CONSISTENT, CONSISTENT)
    assert result["presence_score"] == 1.0
    assert result["status"] == "complet"
