# Jeu de données à grande échelle — 1000 dossiers (évaluation)

Contrairement à `data/dossiers_synthetiques/` (11 dossiers, pensé pour la démo
Streamlit), ce jeu de données sert à **mesurer** la fiabilité du pipeline à
l'échelle : 1000 dossiers candidats synthétiques (CIN, acte de naissance, bac,
licence, relevés L1/L2/L3/M1), avec vérité terrain complète dans `manifest.jsonl`.
Aucune donnée réelle — noms, dates, notes sont entièrement inventés.

Les images (~150 Mo, plus de 8000 fichiers) ne sont **pas versionnées** (voir
`.gitignore`) : seul `manifest.jsonl` (texte, vérité terrain) est commité. Pour
régénérer les images localement :

```
python -m tests.generate_dataset_images --from-manifest
```

## Composition (`_anomalie` dans manifest.jsonl)

| Anomalie | Dossiers | Description |
|---|---|---|
| `coherent` | 700 | Dossier complet et cohérent |
| `nom_mal_orthographie` | 50 | Nom orthographié différemment sur un document |
| `document_bac_manquant` | 50 | Diplôme du bac absent du dossier |
| `annee_licence_incoherente` | 50 | Année d'obtention de la licence incohérente avec les relevés |
| `annee_universitaire_dupliquee` | 50 | Une année universitaire apparaît deux fois dans les relevés |
| `identite_releve_inversee` | 50 | Nom/prénom inversés sur un relevé |
| `moyenne_incoherente_avec_mention` | 50 | Moyenne du relevé incohérente avec la mention du diplôme |

## Évaluation du pipeline sur ce dataset

```
python -m tests.evaluate_pipeline --per-anomalie 15   # ~105 dossiers, quelques minutes
python -m tests.evaluate_pipeline --full                # les 1000 dossiers, plusieurs heures
```

Fait tourner le pipeline réel (prétraitement → OCR → classification → extraction
→ `verification.identity_checker`) sur chaque document et compare aux champs
`ground_truth` du manifeste. Mesure, par type de document, la précision de
classification, le statut d'extraction et l'exactitude champ par champ ; par
type d'anomalie, si `identity_checker` la détecte (attendu seulement sur
`nom_mal_orthographie` et `identite_releve_inversee` : c'est le seul module
existant à ce jour qui compare une forme d'identité entre documents — les 4
autres catégories ne sont pas des anomalies d'identité et ne sont détectées par
aucun module pour l'instant, cf. rapport §9). Écrit un rapport JSON détaillé
dans `data/reports/`.

## Note sur la génération

`tests/generate_dataset_images.py` a été fourni déjà accompagné des images
rendues (`--input` avec le fichier JSON source original n'est pas nécessaire ici
: `manifest.jsonl` contient déjà la vérité terrain complète de chaque dossier).
Un bug de rendu a été corrigé après réception : la largeur de canevas était
fixée à 900px sans retour à la ligne, ce qui rognait silencieusement les valeurs
longues (ex. un nom d'établissement) - illisibles même à l'œil nu, pas seulement
par l'OCR. La largeur est désormais calculée automatiquement à partir de la
ligne la plus longue ; les 1000 dossiers ont été régénérés avec la correction.
