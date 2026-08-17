"""Vérification de la cohérence des années universitaires entre les relevés de
notes d'un dossier, et avec le diplôme de licence (rapport §9 : "vérification
des années universitaires (doublons, années manquantes, erreurs de
classement)"). Comme identity_checker, ce module signale une anomalie sans
jamais décider de la validité du dossier (rapport §1.5) : la décision reste
aux enseignants.
"""
import re

_YEAR_RANGE = re.compile(r"(\d{4})\D+(\d{4})")
_EXPECTED_SEQUENCE = ["L1", "L2", "L3", "M1"]


def _parse_year_range(annee_universitaire: str | None) -> tuple[int, int] | None:
    """Extrait (annee_debut, annee_fin) depuis un texte du type "2021-2022" ou
    "2021/2022", quel que soit le séparateur (variations d'OCR possibles)."""
    if not annee_universitaire:
        return None
    match = _YEAR_RANGE.search(annee_universitaire)
    return (int(match.group(1)), int(match.group(2))) if match else None


def check_academic_years(releves: list[dict], licence_fields: dict | None = None) -> dict:
    """Compare les années universitaires des relevés d'un dossier entre elles,
    et avec l'année d'obtention de la licence si elle est disponible.

    `releves` : liste des champs extraits (ReleveExtractor) pour chaque relevé
    du dossier - `niveau` et `annee_universitaire` sont utilisés quand présents.
    `licence_fields` : champs extraits du diplôme de licence, si fourni.

    Retourne {"consistent": bool, "issues": [str, ...]}.
    """
    issues = []

    # 1) Doublons : deux relevés ne peuvent pas déclarer la même année
    # universitaire (on ne peut pas être dans deux niveaux la même année).
    first_niveau_for_annee: dict[str, str] = {}
    for releve in releves:
        annee = releve.get("annee_universitaire")
        if not annee:
            continue
        if annee in first_niveau_for_annee:
            issues.append(
                f"Deux relevés déclarent la même année universitaire ({annee}) : "
                f"niveau {first_niveau_for_annee[annee]} et niveau {releve.get('niveau', '?')}."
            )
        else:
            first_niveau_for_annee[annee] = releve.get("niveau", "?")

    # 2) Années manquantes : les niveaux fournis doivent suivre L1 -> L2 -> L3
    # -> M1 sans trou (ex. L1 et L3 présents sans L2 = relevé manquant).
    by_niveau = {
        releve["niveau"].strip().upper(): releve
        for releve in releves
        if releve.get("niveau") and releve.get("annee_universitaire")
    }
    niveaux_presents = [n for n in _EXPECTED_SEQUENCE if n in by_niveau]

    if len(niveaux_presents) >= 2:
        indices = [_EXPECTED_SEQUENCE.index(n) for n in niveaux_presents]
        span = _EXPECTED_SEQUENCE[indices[0] : indices[-1] + 1]
        manquants = [n for n in span if n not in niveaux_presents]
        if manquants:
            issues.append(
                f"Relevé(s) manquant(s) dans le parcours : {', '.join(manquants)} "
                f"(présents : {', '.join(niveaux_presents)})."
            )

        # 3) Erreurs de classement : l'année de fin d'un niveau doit être
        # l'année de début du niveau suivant, pour deux niveaux réellement
        # adjacents dans le parcours (un trou entre deux niveaux présents,
        # déjà signalé ci-dessus, ne doit pas déclencher ce message en plus).
        for i in range(len(_EXPECTED_SEQUENCE) - 1):
            niveau_a, niveau_b = _EXPECTED_SEQUENCE[i], _EXPECTED_SEQUENCE[i + 1]
            if niveau_a not in by_niveau or niveau_b not in by_niveau:
                continue
            range_a = _parse_year_range(by_niveau[niveau_a]["annee_universitaire"])
            range_b = _parse_year_range(by_niveau[niveau_b]["annee_universitaire"])
            if range_a and range_b and range_a[1] != range_b[0]:
                issues.append(
                    f"Années incohérentes entre {niveau_a} "
                    f"({by_niveau[niveau_a]['annee_universitaire']}) et {niveau_b} "
                    f"({by_niveau[niveau_b]['annee_universitaire']}) : elles ne se suivent pas."
                )

    # 4) Cohérence avec la licence : elle est délivrée à la fin de la L3 (un
    # éventuel M1, postérieur, ne doit pas être confondu avec ce repère).
    if licence_fields and licence_fields.get("annee_obtention") and "L3" in by_niveau:
        l3_range = _parse_year_range(by_niveau["L3"]["annee_universitaire"])
        try:
            annee_obtention = int(str(licence_fields["annee_obtention"]).strip())
        except ValueError:
            annee_obtention = None
        if l3_range and annee_obtention is not None and annee_obtention != l3_range[1]:
            issues.append(
                f"Année d'obtention de la licence ({annee_obtention}) incohérente avec la fin de "
                f"la L3 ({by_niveau['L3']['annee_universitaire']})."
            )

    return {"consistent": len(issues) == 0, "issues": issues}
