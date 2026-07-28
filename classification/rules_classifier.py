"""Classification par règles des documents (rapport §3.2.3).

Approche par mots-clés pondérés : rapide à mettre en œuvre, explicable, mais
limitée face à des mises en page non anticipées (cf. rapport §4.4 et §8.2).
Candidat naturel à un remplacement par un classifieur ML (TF-IDF + SVM), cf. §4.6.
"""
from config.settings import MIN_CLASSIFICATION_CONFIDENCE
from ocr.text_normalization import normalize

DOCUMENT_TYPES = ["cin", "acte_naissance", "bac", "diplome_licence", "releve_notes"]
UNKNOWN_TYPE = "inconnu"

# {document_type: [(mot-clé normalisé, poids), ...]}
KEYWORD_RULES: dict[str, list[tuple[str, int]]] = {
    "cin": [
        ("carte d'identite nationale", 5),
        ("carte nationale d'identite", 5),
        ("carte d'identite", 3),
        ("n cin", 2),
        ("cin", 1),
        # Carte d'identité tunisienne en arabe (rapport §2.2.1 : détection de nationalité
        # à partir de documents dont l'alphabet peut être arabe). Plusieurs variantes sont
        # listées pour tolérer les erreurs de lecture courantes de l'OCR sur ce script.
        ("بطاقة التعريف الوطنية", 5),
        ("بطاقة تعريف", 4),
        ("التعريف الوطنية", 4),
        ("التعرف الوطني", 3),
        ("تعريف", 2),
        ("التعرف", 2),
        ("بطاقة", 1),
        ("الجمهورية التونسية", 2),
    ],
    "acte_naissance": [
        ("acte de naissance", 5),
        ("extrait d'acte de naissance", 5),
        ("acte de l'etat civil", 4),
        ("etat civil", 2),
        ("fille de", 1),
        ("fils de", 1),
    ],
    "bac": [
        ("diplome du baccalaureat", 5),
        ("baccalaureat", 4),
        ("session", 1),
    ],
    "diplome_licence": [
        ("diplome national de licence", 5),
        ("diplome de licence", 5),
        ("licence", 2),
        ("specialite", 1),
    ],
    "releve_notes": [
        ("releve de notes", 5),
        ("releve des notes", 5),
        ("moyenne generale", 3),
        ("moyenne", 1),
        ("semestre", 1),
        ("unite d'enseignement", 2),
        ("credits", 1),
        ("resultat", 1),
    ],
}


def classify_with_scores(text: str) -> dict[str, int]:
    """Retourne le score brut (somme des poids des mots-clés trouvés) par type de document."""
    normalized = normalize(text)
    return {
        doc_type: sum(weight for keyword, weight in rules if keyword in normalized)
        for doc_type, rules in KEYWORD_RULES.items()
    }


class DocumentClassifier:
    """Classifieur par règles (cf. diagramme de classes, rapport §3.5)."""

    def classify_with_confidence(self, text: str) -> dict:
        scores = classify_with_scores(text)
        total = sum(scores.values())
        best_type = max(scores, key=scores.get) if scores else UNKNOWN_TYPE
        best_score = scores.get(best_type, 0)
        confidence = (best_score / total) if total > 0 else 0.0

        if best_score == 0 or confidence < MIN_CLASSIFICATION_CONFIDENCE:
            best_type = UNKNOWN_TYPE
            confidence = 0.0

        return {"document_type": best_type, "confidence": round(confidence, 2), "scores": scores}

    def classify(self, text: str) -> str:
        return self.classify_with_confidence(text)["document_type"]
