"""Vérification de la cohérence d'identité entre les documents d'un dossier
(rapport §2.2.4, §3.2.5).

Compare les champs d'identité (nom, prénom) de tous les documents qui en
exposent un, et signale toute divergence - sans jamais décider de la validité
du dossier (rapport §1.5) : la décision reste aux enseignants. Deux formes de
divergence sont distinguées :
  - des mots différents (typiquement une personne différente, ou une faute
    d'orthographe importante) - comparaison par similarité d'ensemble (indice
    de Jaccard), tolérante au bruit OCR ;
  - les mêmes mots dans un ordre différent (nom et prénom inversés sur un
    document, ex. relevé de notes) - invisible à une comparaison par ensemble
    puisque l'ensemble de mots est identique ; détectée séparément par
    comparaison de séquence, mesurée à l'évaluation à grande échelle
    (data/samples_dataset/, anomalie "identite_releve_inversee") : la
    comparaison par ensemble seule ne détectait que 13% de ces inversions.

Limite connue : la comparaison est fondée sur la similarité textuelle des noms
normalisés. Elle est fiable au sein d'une même écriture (ex. deux documents en
français), mais ne peut pas rapprocher un nom écrit en arabe de sa
translittération française - un cas qui nécessiterait une translittération
dédiée, hors périmètre de ce POC (cf. rapport §8.3).
"""
from ocr.text_normalization import normalize

MIN_JACCARD_SIMILARITY = 0.5


def _name_sequence(fields: dict) -> list[str] | None:
    """Extrait les mots du nom complet d'un document, dans l'ordre où
    l'extracteur les expose (nom puis prénom pour la plupart des documents, ou
    "etudiant" combiné pour un relevé de notes) - nécessaire pour détecter une
    inversion nom/prénom, qu'un ensemble de mots ne peut pas voir."""
    parts = [fields[k] for k in ("nom", "prenom") if fields.get(k)]
    if not parts and fields.get("etudiant"):
        parts = [fields["etudiant"]]
    if not parts:
        return None
    sequence = [t for part in parts for t in normalize(part).split() if len(t) >= 2]
    return sequence or None


def _is_word_order_swap(reference_sequence: list[str], other_sequence: list[str]) -> bool:
    """Vrai si les deux séquences contiennent exactement les mêmes mots dans un
    ordre différent (ex. "Aymen BEN AMOR" vs "BEN AMOR Aymen") - à distinguer
    d'un simple bruit OCR sur un mot (ex. "SALMA" vs "SALMA*"), qui change le
    multi-ensemble de mots et ne doit pas être signalé comme une inversion."""
    return reference_sequence != other_sequence and sorted(reference_sequence) == sorted(other_sequence)


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
        sequence = _name_sequence(doc["fields"])
        if sequence:
            usable.append({"label": doc["label"], "sequence": sequence, "fields": doc["fields"]})

    issues = []
    reference = usable[0] if usable else None
    for other in usable[1:]:
        reference_tokens, other_tokens = set(reference["sequence"]), set(other["sequence"])
        intersection = reference_tokens & other_tokens
        union = reference_tokens | other_tokens
        similarity = len(intersection) / len(union) if union else 1.0

        if similarity < MIN_JACCARD_SIMILARITY:
            issues.append(
                f"Identité incohérente entre « {reference['label']} » "
                f"({_display_name(reference['fields'])}) et « {other['label']} » "
                f"({_display_name(other['fields'])})."
            )
        elif _is_word_order_swap(reference["sequence"], other["sequence"]):
            issues.append(
                f"Nom et prénom potentiellement inversés entre « {reference['label']} » "
                f"({_display_name(reference['fields'])}) et « {other['label']} » "
                f"({_display_name(other['fields'])})."
            )

    return {
        "consistent": len(issues) == 0,
        "comparable_documents": len(usable),
        "issues": issues,
    }
