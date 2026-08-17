"""Tests de la vérification de cohérence d'identité (rapport §2.2.4, §3.2.5)."""
from verification.identity_checker import check_identity_consistency


def test_consistent_dossier_has_no_issues():
    documents = [
        {"label": "CIN", "fields": {"nom": "BEN ALI", "prenom": "SALMA"}},
        {"label": "Acte de naissance", "fields": {"nom": "BEN ALI", "prenom": "SALMA"}},
        {"label": "Relevé de notes", "fields": {"etudiant": "BEN ALI SALMA"}},
    ]
    result = check_identity_consistency(documents)
    assert result["consistent"] is True
    assert result["issues"] == []
    assert result["comparable_documents"] == 3


def test_inconsistent_dossier_is_flagged():
    documents = [
        {"label": "CIN", "fields": {"nom": "BEN ALI", "prenom": "SALMA"}},
        {"label": "Acte de naissance", "fields": {"nom": "BARAKATI", "prenom": "MOUNIR"}},
    ]
    result = check_identity_consistency(documents)
    assert result["consistent"] is False
    assert len(result["issues"]) == 1
    assert "CIN" in result["issues"][0]
    assert "Acte de naissance" in result["issues"][0]


def test_documents_without_identity_fields_are_ignored():
    documents = [
        {"label": "CIN", "fields": {"nom": "BEN ALI", "prenom": "SALMA"}},
        {"label": "Bac", "fields": {"annee_obtention": "2019"}},
    ]
    result = check_identity_consistency(documents)
    assert result["consistent"] is True
    assert result["comparable_documents"] == 1


def test_empty_dossier_is_consistent_by_default():
    result = check_identity_consistency([])
    assert result["consistent"] is True
    assert result["comparable_documents"] == 0


def test_minor_ocr_noise_does_not_trigger_false_positive():
    documents = [
        {"label": "CIN", "fields": {"nom": "BEN ALI", "prenom": "SALMA"}},
        {"label": "Bac", "fields": {"nom": "BEN ALI", "prenom": "SALMA*"}},
    ]
    result = check_identity_consistency(documents)
    assert result["consistent"] is True


def test_nom_prenom_swap_is_flagged_even_with_identical_word_set():
    # Mêmes mots que la référence, mais dans un ordre différent : invisible à
    # une comparaison par ensemble (même jeu de tokens), doit être détecté par
    # comparaison de séquence (cf. rapport, anomalie "identite_releve_inversee").
    documents = [
        {"label": "CIN", "fields": {"nom": "BEN AMOR", "prenom": "Aymen"}},
        {"label": "Relevé de notes", "fields": {"etudiant": "Aymen BEN AMOR"}},
    ]
    result = check_identity_consistency(documents)
    assert result["consistent"] is False
    assert "invers" in result["issues"][0]
