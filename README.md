# ESPRIT Admission POC — Vérification automatique des dossiers de candidature

Proof of Concept développé dans le cadre du stage de fin d'études :
prétraitement OpenCV → OCR Tesseract → classification par règles → extraction structurée
(Sprint 1 & 2), complété par une vérification de cohérence d'identité entre documents et
une génération de questions d'entretien via LLM (début de Sprint 3).

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

## Interface Streamlit

```
streamlit run app.py
```

Un emplacement de dépôt par type de document (CIN, acte de naissance, bac, licence,
relevé de notes), avec vérification automatique de la cohérence d'identité entre les
documents déposés et génération de questions d'entretien.

Pour activer la génération de questions (Module 2, LLM), définir la variable
d'environnement `OPENAI_API_KEY` ou la saisir directement dans l'interface (jamais
enregistrée sur le disque).

## Arborescence

```
config/            Paramètres (langues OCR, chemin Tesseract, seuils)
preprocessing/      Prétraitement OpenCV (contraste, bruit, redimensionnement, deskew)
ocr/                Interface avec Tesseract
classification/     Classification par règles (5 types de documents)
extraction/         Extracteurs spécialisés + contrat JSON commun
verification/       Vérification de cohérence d'identité entre documents (Sprint 3)
interview/          Génération de questions d'entretien via LLM (Sprint 3, Module 2)
models/             Structures de données (Document, ExtractionResult, CandidateFile)
tests/              Tests unitaires + générateur de documents d'exemple
data/samples/       Documents d'exemple (générés)
data/reports/       Rapports JSON produits par le pipeline
app.py              Interface Streamlit
```

Le score de complétude global du dossier (années universitaires, niveau académique,
détection de doublons) reste à implémenter (suite du Sprint 3).
