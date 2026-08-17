"""Détection de documents dupliqués dans un dossier (rapport §9) : le même
document physique déposé deux fois, accidentellement, dans des emplacements
différents (ex. le même relevé de L2 téléversé deux fois). Compare le texte
OCR brut de chaque paire de documents plutôt que les champs déjà extraits,
pour rester indépendant du type de document - deux documents de types
différents ne seront jamais jugés dupliqués. Comme les autres modules de
verification/, signale sans jamais décider de la validité du dossier
(rapport §1.5).
"""
from difflib import SequenceMatcher

from ocr.text_normalization import normalize

MIN_DUPLICATE_SIMILARITY = 0.9


def check_duplicate_documents(documents: list[dict]) -> dict:
    """Compare le texte OCR de chaque paire de documents du dossier.

    `documents` : liste de {"label": str, "raw_text": str}.

    Retourne {"consistent": bool, "issues": [str, ...]}.
    """
    usable = [
        {"label": doc["label"], "text": normalize(doc.get("raw_text") or "")}
        for doc in documents
        if (doc.get("raw_text") or "").strip()
    ]

    issues = []
    for i in range(len(usable)):
        for j in range(i + 1, len(usable)):
            similarity = SequenceMatcher(None, usable[i]["text"], usable[j]["text"]).ratio()
            if similarity >= MIN_DUPLICATE_SIMILARITY:
                issues.append(
                    f"« {usable[i]['label']} » et « {usable[j]['label']} » semblent être le même "
                    f"document déposé deux fois (similarité {similarity:.0%})."
                )

    return {"consistent": len(issues) == 0, "issues": issues}
