"""Tests de la vérification de cohérence des années universitaires (rapport §9)."""
from verification.academic_years_checker import check_academic_years


def test_consistent_years_have_no_issues():
    releves = [
        {"niveau": "L1", "annee_universitaire": "2021-2022"},
        {"niveau": "L2", "annee_universitaire": "2022-2023"},
        {"niveau": "L3", "annee_universitaire": "2023-2024"},
    ]
    licence_fields = {"annee_obtention": "2024"}
    result = check_academic_years(releves, licence_fields)
    assert result["consistent"] is True
    assert result["issues"] == []


def test_duplicate_annee_universitaire_is_flagged():
    releves = [
        {"niveau": "L1", "annee_universitaire": "2021-2022"},
        {"niveau": "L2", "annee_universitaire": "2022-2023"},
        {"niveau": "L3", "annee_universitaire": "2022-2023"},
    ]
    result = check_academic_years(releves)
    assert result["consistent"] is False
    assert "même année universitaire" in result["issues"][0]


def test_missing_level_in_sequence_is_flagged():
    releves = [
        {"niveau": "L1", "annee_universitaire": "2021-2022"},
        {"niveau": "L3", "annee_universitaire": "2023-2024"},
    ]
    result = check_academic_years(releves)
    assert result["consistent"] is False
    assert "manquant" in result["issues"][0]
    assert "L2" in result["issues"][0]


def test_non_consecutive_years_between_adjacent_levels_is_flagged():
    releves = [
        {"niveau": "L1", "annee_universitaire": "2021-2022"},
        {"niveau": "L2", "annee_universitaire": "2023-2024"},  # devrait commencer en 2022
    ]
    result = check_academic_years(releves)
    assert result["consistent"] is False
    assert "ne se suivent pas" in result["issues"][0]


def test_licence_annee_obtention_inconsistent_with_l3_is_flagged():
    releves = [{"niveau": "L3", "annee_universitaire": "2023-2024"}]
    result = check_academic_years(releves, {"annee_obtention": "2025"})
    assert result["consistent"] is False
    assert "licence" in result["issues"][0]


def test_m1_after_licence_does_not_trigger_false_positive():
    # La licence est délivrée à la fin de la L3 ; un M1 postérieur est normal
    # et ne doit pas être comparé à l'année d'obtention de la licence.
    releves = [
        {"niveau": "L3", "annee_universitaire": "2023-2024"},
        {"niveau": "M1", "annee_universitaire": "2024-2025"},
    ]
    result = check_academic_years(releves, {"annee_obtention": "2024"})
    assert result["consistent"] is True


def test_no_releves_is_consistent_by_default():
    result = check_academic_years([])
    assert result["consistent"] is True
    assert result["issues"] == []


def test_releve_without_niveau_does_not_crash():
    releves = [{"annee_universitaire": "2021-2022"}, {"annee_universitaire": "2022-2023"}]
    result = check_academic_years(releves)
    assert result["consistent"] is True
