"""Tests du module de génération de questions d'entretien (rapport §3.3)."""
import pytest

from interview.question_generator import (
    LLMNotConfiguredError,
    _build_mock_interview_feedback_prompt,
    build_candidate_profile,
    generate_interview_feedback,
    generate_interview_questions,
)


def test_build_candidate_profile_aggregates_dossier_fields():
    documents = [
        {"document_type": "cin", "fields": {"nom": "BEN ALI", "prenom": "SALMA"}},
        {
            "document_type": "diplome_licence",
            "fields": {"specialite": "Informatique de Gestion", "annee_obtention": "2024", "etablissement": "FST"},
        },
        {"document_type": "bac", "fields": {"filiere_bac": "Sciences Informatiques", "mention": "Assez Bien"}},
        {
            "document_type": "releve_notes",
            "fields": {
                "annee_universitaire": "2022/2023",
                "moyenne": "14.16",
                "matieres": [
                    {"matiere": "Algorithmique", "note": 14.5},
                    {"matiere": "Bases de donnees", "note": 13.0},
                    {"matiere": "Reseaux", "note": 15.0},
                ],
            },
        },
    ]
    profile = build_candidate_profile(documents)

    assert profile["nom_complet"] == "BEN ALI SALMA"
    assert profile["specialite_licence"] == "Informatique de Gestion"
    assert profile["filiere_bac"] == "Sciences Informatiques"
    assert len(profile["releves"]) == 1
    assert profile["matieres_les_mieux_evaluees"][0]["matiere"] == "Reseaux"
    assert profile["matieres_les_mieux_evaluees"][0]["note"] == 15.0


def test_generate_interview_questions_without_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMNotConfiguredError):
        generate_interview_questions({"nom_complet": "TEST"}, api_key=None)


def test_generate_interview_feedback_without_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    qa_pairs = [{"question": "Pourquoi cette spécialité ?", "reponse": "Parce que..."}]
    with pytest.raises(LLMNotConfiguredError):
        generate_interview_feedback({"nom_complet": "TEST"}, qa_pairs, api_key=None)


def test_mock_interview_feedback_prompt_forbids_admission_verdict():
    # Garde-fou (rapport §1.5) : le prompt envoyé au LLM doit rappeler
    # explicitement qu'aucun verdict d'admission n'est attendu, même si le
    # prompt système est ignoré ou tronqué par le fournisseur LLM.
    prompt = _build_mock_interview_feedback_prompt(
        {"nom_complet": "TEST"}, [{"question": "Q1", "reponse": "R1"}]
    )
    assert "verdict d'admission" in prompt
    assert "points_forts" in prompt
    assert "axes_amelioration" in prompt
    assert "conseils_preparation" in prompt
