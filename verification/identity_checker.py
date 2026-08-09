"""Vérification de la cohérence d'identité entre les documents d'un dossier
(rapport §2.2.4, §3.2.5).

Compare les champs d'identité (nom, prénom) de tous les documents qui en
exposent un, et signale toute divergence - sans jamais décider de la validité
du dossier (rapport §1.5) : la décision reste aux enseignants.

Limite connue : la comparaison est fondée sur la similarité textuelle des noms
normalisés (ensemble de mots communs). Elle est fiable au sein d'une même
écriture (ex. deux documents en français), mais ne peut pas rapprocher un nom
écrit en arabe de sa translittération française - un cas qui nécessiterait une
translittération dédiée, hors périmètre de ce POC (cf. rapport §8.3).
"""
from ocr.text_normalization import normalize

MIN_JACCARD_SIMILARITY = 0.5


def _name_tokens(fields: dict) -> set[str] | None:
    """Extrait l'ensemble des mots du nom complet d'un document, quelle que soit
    la façon dont l'extracteur a exposé l'identité (nom+prenom séparés pour la
    plupart des documents, ou "etudiant" combiné pour un relevé de notes)."""
    parts = [fields[k] for k in ("nom", "prenom") if fields.get(k)]
    if not parts and fields.get("etudiant"):
        parts = [fields["etudiant"]]
    if not parts:
        return None
    tokens = set()
    for part in parts:
        tokens.update(t for t in normalize(part).split() if len(t) >= 2)
    return tokens or None


def _display_name(fields: dict) -> str:
    if fields.get("nom") or fields.get("prenom"):
        return " ".join(v for v in (fields.get("nom"), fields.get("prenom")) if v)
    return fields.get("etudiant", "?")


def check_identity_consistency(documents: list[dict]) -> dict:
    """Compare l'identité entre tous les documents comparables d'un dossier.

    `documents` : liste de {"label": str, "fields": dict}, un élément par
    document du dossier (label = intitulé lisible, ex. "Carte d'identité
    nationale (CIN)").

    Retourne :
    {
      "consistent": bool,           # aucune divergence détectée
      "comparable_documents": int,  # nombre de documents exploités pour la comparaison
      "issues": [str, ...],         # une phrase par divergence détectée
    }
    """
    usable = []
    for doc in documents:
        tokens = _name_tokens(doc["fields"])
        if tokens:
            usable.append({"label": doc["label"], "tokens": tokens, "fields": doc["fields"]})

    issues = []
    reference = usable[0] if usable else None
    for other in usable[1:]:
        intersection = reference["tokens"] & other["tokens"]
        union = reference["tokens"] | other["tokens"]
        similarity = len(intersection) / len(union) if union else 1.0
        if similarity < MIN_JACCARD_SIMILARITY:
            issues.append(
                f"Identité incohérente entre « {reference['label']} » "
                f"({_display_name(reference['fields'])}) et « {other['label']} » "
                f"({_display_name(other['fields'])})."
            )

    return {
        "consistent": len(issues) == 0,
        "comparable_documents": len(usable),
        "issues": issues,
    }
