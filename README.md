# ESPRIT Admission POC — Vérification automatique des dossiers de candidature

Proof of Concept développé dans le cadre du stage de fin d'études (Sprint 1 & 2) :
prétraitement OpenCV → OCR Tesseract → classification par règles → extraction structurée.

Le système **n'émet aucune décision d'admission** : il produit un rapport JSON destiné
à assister les enseignants dans la vérification des dossiers (voir rapport de stage,
chapitre 1.5).

## Installation

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Tesseract OCR doit être installé sur le poste (langues `fra`, `ara`, `eng`). Si le
binaire n'est pas dans le PATH, définir la variable d'environnement `TESSERACT_CMD`
avec le chemin complet vers `tesseract.exe` (voir `config/settings.py`).

## Génération des documents d'exemple

Aucun scan réel n'étant disponible pour ce POC, un jeu de documents synthétiques
(texte rendu en image) est généré pour valider la chaîne de traitement de bout en bout :

```
python -m tests.sample_documents
```

Cela crée 5 images dans `data/samples/` (cin, acte de naissance, bac, licence, relevé de notes).

## Exécution du pipeline

```
python main.py
```

Traite tous les documents de `data/samples/`, affiche le contrat JSON de chaque
document et écrit le rapport agrégé dans `data/reports/`.

## Tests

```
pytest -v
```

## Arborescence (Sprint 1 & 2)

```
config/            Paramètres (langues OCR, chemin Tesseract, seuils)
preprocessing/      Prétraitement OpenCV (contraste, bruit, redimensionnement, deskew)
ocr/                Interface avec Tesseract
classification/     Classification par règles (5 types de documents)
extraction/         Extracteurs spécialisés + contrat JSON commun
models/             Structures de données (Document, ExtractionResult, CandidateFile)
tests/              Tests unitaires + générateur de documents d'exemple
data/samples/       Documents d'exemple (générés)
data/reports/       Rapports JSON produits par le pipeline
```

La vérification de cohérence, le score de complétude et la génération de questions
d'entretien (LLM) relèvent du Sprint 3 et ne sont pas couverts ici.
