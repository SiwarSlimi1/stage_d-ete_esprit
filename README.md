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

## Jeu de données synthétique diversifié (dossiers complets)

Les vrais dossiers de candidats étant confidentiels (consigne de l'encadrante,
rapport §10), un second générateur produit 11 dossiers candidats fictifs complets
(CIN, acte de naissance, bac, licence, relevés L1/L2/L3/M1), dont 5 valides et 6
avec une anomalie volontaire (identité incohérente, document manquant, années
incohérentes, dates incohérentes, année ajournée, document dupliqué) :

```
python -m tests.generate_synthetic_dataset
```

Crée les dossiers et `manifest.json` dans `data/dossiers_synthetiques/` — voir le
`README.md` de ce dossier pour le détail de chaque scénario.

## Évaluation à grande échelle (1000 dossiers)

`data/samples_dataset/` contient un jeu de 1000 dossiers synthétiques avec vérité
terrain (`manifest.jsonl`), utilisé pour mesurer la fiabilité réelle du pipeline
(précision de classification, exactitude champ par champ, taux de détection des
6 types d'anomalies) plutôt que de se limiter aux 38 tests unitaires sur un seul
candidat. Voir `data/samples_dataset/README.md`.

```
python -m tests.generate_dataset_images --from-manifest   # régénère les images (non versionnées)
python -m tests.evaluate_pipeline --per-anomalie 15        # évalue le pipeline (~105 dossiers)
```

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
verification/       Cohérence entre documents + score de complétude du dossier (Sprint 3)
interview/          Génération de questions d'entretien via LLM (Sprint 3, Module 2)
models/             Structures de données (Document, ExtractionResult, CandidateFile)
tests/              Tests unitaires + générateur de documents d'exemple
data/samples/       Documents d'exemple (générés)
data/reports/       Rapports JSON produits par le pipeline
app.py              Interface Streamlit
```

Le score de complétude global du dossier (présence des documents attendus, complétude
de l'extraction, résultat des 3 vérifications de cohérence) est calculé par
`verification/completeness_score.py`, avec un barème par défaut ajustable dans
`config/settings.py` — aucun barème officiel n'ayant été fourni par l'encadrante à ce
jour (rapport §10). Le niveau académique (moyennes minimales, mentions attendues) reste
hors périmètre, faute de critère d'admission défini.
