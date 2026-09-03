# Jeu de données synthétique — dossiers candidats

Généré par `tests/generate_synthetic_dataset.py` (`python -m tests.generate_synthetic_dataset`).

**Aucune donnée réelle.** Les vrais dossiers de candidats (CIN, actes de naissance,
relevés...) sont confidentiels et ne peuvent pas être utilisés pour ce POC ni
versionnés (consigne de l'encadrante, cf. rapport §10). Les 11 dossiers ci-dessous
sont entièrement fictifs : noms, numéros de CIN, dates et notes sont inventés. Ils
remplacent les documents réels pour tester le pipeline et les règles métier du
Sprint 3 sans jamais manipuler d'information personnelle véritable.

Chaque dossier contient : `cin.png`, `acte_naissance.png`, `bac.png`,
`diplome_licence.png`, et un `releve_<niveau>.png` par année (L1, L2, L3, parfois
M1) — le détail est dans `manifest.json`.

## Dossiers valides (5)

Cohérents de bout en bout (identité, dates, années universitaires qui s'enchaînent) :
`01_valide_trabelsi_youssef`, `02_valide_gharbi_amira`, `03_valide_saidane_mohamed`,
`04_valide_mansouri_ines` (avec une année de M1 en plus), `05_valide_chaabane_karim`.
Cinq filières différentes (informatique, génie civil, génie électrique, informatique
de gestion, génie mécanique) pour diversifier les relevés.

## Dossiers avec anomalie volontaire (6)

| Dossier | Anomalie | Détecté aujourd'hui par... |
|---|---|---|
| `06_incoherence_identite_jendoubi_rania` | Prénom différent sur l'acte de naissance (RAYEN au lieu de RANIA) | ✅ `verification/identity_checker.py` |
| `07_document_manquant_bouazizi_sami` | Acte de naissance absent du dossier | ✅ `verification/completeness_score.py` (statut "documents_manquants") |
| `08_annees_incoherentes_werghi_nadia` | Relevé de L2 manquant (la L3 suit directement la L1) | ✅ `verification/academic_years_checker.py` |
| `09_dates_incoherentes_fejjari_hedi` | Date de naissance différente entre CIN et acte de naissance | ✅ `verification/identity_checker.py` (comparaison de date, en plus du nom) |
| `10_echec_annee_ayari_emna` | L2 ajournée (moyenne 8.40) puis parcours interrompu | ❌ pas encore (critère de niveau académique conforme non défini) |
| `11_document_duplique_sassi_yassine` | Relevé de L2 déposé deux fois (`releve_l2.png` et `releve_l2_bis.png`, contenu identique) | ✅ `verification/duplicate_document_checker.py` |

Ce tableau reprend exactement les points ouverts du rapport §9 ("Ce qu'il reste à
faire") : chaque anomalie non détectée aujourd'hui est un cas de test prêt à
l'emploi pour la fonctionnalité correspondante, une fois implémentée.

## Vérification

Les 76 documents ont été passés dans le pipeline réel (prétraitement → OCR →
classification → extraction) : 76/76 en `extraction_status: "success"`, et seuls
les dossiers `06_incoherence_identite...` (nom) et `09_dates_incoherentes...`
(date de naissance) déclenchent une alerte `identity_checker`, comme prévu -
aucun faux positif sur les 5 dossiers valides.

## Régénérer le jeu de données

```
python -m tests.generate_synthetic_dataset
```

Écrase le contenu de ce dossier et régénère `manifest.json`.
