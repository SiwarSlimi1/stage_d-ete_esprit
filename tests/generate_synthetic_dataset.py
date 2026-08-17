"""Génère un jeu de données synthétique diversifié : plusieurs dossiers candidats
complets (CIN, acte de naissance, bac, licence, relevés L1/L2/L3/M1), certains
volontairement invalides.

Contexte (rapport §10) : les vrais dossiers de candidats sont confidentiels et ne
peuvent pas quitter le poste local ni être versionnés. `tests/sample_documents.py`
ne fournit qu'un seul exemplaire de chaque type de document (un seul candidat), ce
qui suffit à valider le pipeline mais pas à tester les règles métier du Sprint 3
(cohérence entre années, dossier incomplet, documents dupliqués...). Ce générateur
produit donc plusieurs dossiers fictifs, dont certains contiennent une anomalie
délibérée, pour disposer d'un jeu de test réaliste sans jamais utiliser de données
personnelles réelles.

Usage : python -m tests.generate_synthetic_dataset
"""
import json
import unicodedata
from pathlib import Path

from config.settings import DATA_DIR
from tests.sample_documents import render_text_image

OUTPUT_DIR = DATA_DIR / "dossiers_synthetiques"

# ---------------------------------------------------------------------------
# Matières par filière et par niveau (purement fictif, pour diversifier les
# relevés au-delà du seul exemple "informatique" de tests/sample_documents.py).
# ---------------------------------------------------------------------------
MATIERES_PAR_FILIERE = {
    "INFORMATIQUE": {
        "L1": ["Algorithmique", "Analyse 1", "Algebre 1", "Bases de donnees", "Anglais"],
        "L2": ["Structures de donnees", "Analyse 2", "Systemes d'exploitation", "Reseaux", "Probabilites"],
        "L3": ["Genie logiciel", "Intelligence artificielle", "Securite informatique", "Projet de fin d'etudes"],
        "M1": ["Machine Learning avance", "Cloud Computing", "Gestion de projet", "Memoire de recherche"],
    },
    "GENIE CIVIL": {
        "L1": ["Resistance des materiaux", "Analyse 1", "Algebre 1", "Dessin technique", "Anglais"],
        "L2": ["Beton arme", "Mecanique des sols", "Topographie", "Hydraulique", "Probabilites"],
        "L3": ["Structures metalliques", "Geotechnique", "Chantier et securite", "Projet de fin d'etudes"],
    },
    "GENIE ELECTRIQUE": {
        "L1": ["Electricite generale", "Analyse 1", "Algebre 1", "Electronique", "Anglais"],
        "L2": ["Electrotechnique", "Automatique", "Traitement du signal", "Systemes embarques", "Probabilites"],
        "L3": ["Electronique de puissance", "Automatisation industrielle", "Reseaux electriques", "Projet de fin d'etudes"],
    },
    "INFORMATIQUE DE GESTION": {
        "L1": ["Comptabilite generale", "Analyse 1", "Algorithmique", "Bases de donnees", "Anglais"],
        "L2": ["Gestion financiere", "Analyse economique", "Systemes d'information", "Marketing", "Probabilites"],
        "L3": ["ERP et progiciels de gestion", "Audit informatique", "Droit des affaires", "Projet de fin d'etudes"],
        "M1": ["Business Intelligence", "Gouvernance des systemes d'information", "Gestion de projet", "Memoire de recherche"],
    },
    "GENIE MECANIQUE": {
        "L1": ["Mecanique generale", "Analyse 1", "Algebre 1", "Dessin industriel", "Anglais"],
        "L2": ["Resistance des materiaux", "Thermodynamique", "Conception assistee", "Fabrication mecanique", "Probabilites"],
        "L3": ["Mecanique des fluides", "Automatisation", "Maintenance industrielle", "Projet de fin d'etudes"],
    },
}


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.lower().replace(" ", "-").replace("'", "")


def _notes_matieres(matieres: list[str], moyenne_cible: float) -> list[tuple[str, float]]:
    """Génère des notes par matière qui font (à peu près) la moyenne cible, avec
    une petite variation déterministe pour rester crédible (pas toutes égales)."""
    ecarts = [1.4, -0.8, 0.6, -1.1, 0.3][: len(matieres)]
    return [(m, round(max(4.0, min(19.5, moyenne_cible + e)), 2)) for m, e in zip(matieres, ecarts)]


def cin_text(nom: str, prenom: str, date_naissance: str, lieu_naissance: str, numero: str) -> str:
    return f"""REPUBLIQUE TUNISIENNE
CARTE D'IDENTITE NATIONALE

Nom: {nom}
Prenom: {prenom}
Date de naissance: {date_naissance}
Lieu de naissance: {lieu_naissance}
Nationalite: TUNISIENNE
N CIN: {numero}"""


def acte_naissance_text(nom: str, prenom: str, date_naissance: str, lieu_naissance: str, filiation: str) -> str:
    return f"""REPUBLIQUE TUNISIENNE
ACTE DE NAISSANCE
Extrait du registre de l'etat civil

Nom: {nom}
Prenom: {prenom}
Date de naissance: {date_naissance}
Lieu de naissance: {lieu_naissance}
{filiation}"""


def bac_text(nom: str, prenom: str, session: str, filiere: str, mention: str) -> str:
    return f"""REPUBLIQUE TUNISIENNE
MINISTERE DE L'EDUCATION
DIPLOME DU BACCALAUREAT

Nom: {nom}
Prenom: {prenom}
Session: {session}
Filiere: {filiere}
Mention: {mention}"""


def licence_text(nom: str, prenom: str, specialite: str, annee_obtention: str, etablissement: str) -> str:
    return f"""REPUBLIQUE TUNISIENNE
MINISTERE DE L'ENSEIGNEMENT SUPERIEUR
DIPLOME NATIONAL DE LICENCE

Nom: {nom}
Prenom: {prenom}
Specialite: {specialite}
Annee d'obtention: {annee_obtention}
Etablissement: {etablissement}"""


def releve_text(nom: str, prenom: str, niveau: str, annee: str, filiere: str, moyenne: float, resultat: str) -> str:
    matieres = MATIERES_PAR_FILIERE[filiere][niveau]
    lignes_notes = "\n".join(f"{matiere}: {note}" for matiere, note in _notes_matieres(matieres, moyenne))
    return f"""RELEVE DE NOTES
Annee universitaire: {annee}
Niveau: {niveau}
Etudiant: {nom} {prenom}

{lignes_notes}

Moyenne generale: {moyenne}
Resultat: {resultat}"""


# ---------------------------------------------------------------------------
# 11 dossiers candidats fictifs : 6 valides et cohérents, 5 avec une anomalie
# volontaire différente à chaque fois (rapport §10 : "dossiers candidats
# complets, valides ET volontairement invalides"). Aucune de ces personnes
# n'existe ; noms, numéros de CIN et dates sont entièrement inventés.
# ---------------------------------------------------------------------------
CANDIDATES = [
    {
        "id": "01_valide_trabelsi_youssef",
        "scenario": "valide",
        "description": "Dossier complet et cohérent (L1 à L3, informatique).",
        "nom": "TRABELSI", "prenom": "YOUSSEF", "genre": "M",
        "date_naissance": "14/02/2003", "lieu_naissance": "SFAX", "cin_numero": "07845213",
        "pere": "MONCEF TRABELSI", "mere": "LEILA HAMDI",
        "bac_session": "2021", "bac_filiere": "SCIENCES TECHNIQUES", "bac_mention": "BIEN",
        "filiere": "INFORMATIQUE",
        "licence_specialite": "INFORMATIQUE", "licence_annee": "2024",
        "licence_etablissement": "FACULTE DES SCIENCES DE SFAX",
        "releves": [
            {"niveau": "L1", "annee": "2021/2022", "moyenne": 13.2, "resultat": "VALIDE"},
            {"niveau": "L2", "annee": "2022/2023", "moyenne": 13.8, "resultat": "VALIDE"},
            {"niveau": "L3", "annee": "2023/2024", "moyenne": 14.5, "resultat": "VALIDE"},
        ],
    },
    {
        "id": "02_valide_gharbi_amira",
        "scenario": "valide",
        "description": "Dossier complet et cohérent (L1 à L3, génie civil).",
        "nom": "GHARBI", "prenom": "AMIRA", "genre": "F",
        "date_naissance": "03/07/2002", "lieu_naissance": "SOUSSE", "cin_numero": "06612940",
        "pere": "RIDHA GHARBI", "mere": "SAMIA JLASSI",
        "bac_session": "2020", "bac_filiere": "SCIENCES TECHNIQUES", "bac_mention": "ASSEZ BIEN",
        "filiere": "GENIE CIVIL",
        "licence_specialite": "GENIE CIVIL", "licence_annee": "2023",
        "licence_etablissement": "ECOLE NATIONALE D'INGENIEURS DE SOUSSE",
        "releves": [
            {"niveau": "L1", "annee": "2020/2021", "moyenne": 12.4, "resultat": "VALIDE"},
            {"niveau": "L2", "annee": "2021/2022", "moyenne": 12.9, "resultat": "VALIDE"},
            {"niveau": "L3", "annee": "2022/2023", "moyenne": 13.6, "resultat": "VALIDE"},
        ],
    },
    {
        "id": "03_valide_saidane_mohamed",
        "scenario": "valide",
        "description": "Dossier complet et cohérent (L1 à L3, génie électrique).",
        "nom": "SAIDANE", "prenom": "MOHAMED", "genre": "M",
        "date_naissance": "19/11/2002", "lieu_naissance": "BIZERTE", "cin_numero": "05398761",
        "pere": "SLAH SAIDANE", "mere": "NAJET BOUZID",
        "bac_session": "2021", "bac_filiere": "SCIENCES TECHNIQUES", "bac_mention": "BIEN",
        "filiere": "GENIE ELECTRIQUE",
        "licence_specialite": "GENIE ELECTRIQUE", "licence_annee": "2024",
        "licence_etablissement": "ISET DE BIZERTE",
        "releves": [
            {"niveau": "L1", "annee": "2021/2022", "moyenne": 14.0, "resultat": "VALIDE"},
            {"niveau": "L2", "annee": "2022/2023", "moyenne": 13.5, "resultat": "VALIDE"},
            {"niveau": "L3", "annee": "2023/2024", "moyenne": 14.8, "resultat": "VALIDE"},
        ],
    },
    {
        "id": "04_valide_mansouri_ines",
        "scenario": "valide",
        "description": "Dossier complet et cohérent, avec une année de M1 en plus (informatique de gestion).",
        "nom": "MANSOURI", "prenom": "INES", "genre": "F",
        "date_naissance": "27/01/2001", "lieu_naissance": "TUNIS", "cin_numero": "04127658",
        "pere": "KAMEL MANSOURI", "mere": "WIDED SAIDI",
        "bac_session": "2019", "bac_filiere": "SCIENCES DE GESTION", "bac_mention": "ASSEZ BIEN",
        "filiere": "INFORMATIQUE DE GESTION",
        "licence_specialite": "INFORMATIQUE DE GESTION", "licence_annee": "2022",
        "licence_etablissement": "ISG TUNIS",
        "releves": [
            {"niveau": "L1", "annee": "2019/2020", "moyenne": 12.8, "resultat": "VALIDE"},
            {"niveau": "L2", "annee": "2020/2021", "moyenne": 13.1, "resultat": "VALIDE"},
            {"niveau": "L3", "annee": "2021/2022", "moyenne": 13.4, "resultat": "VALIDE"},
            {"niveau": "M1", "annee": "2022/2023", "moyenne": 14.2, "resultat": "VALIDE"},
        ],
    },
    {
        "id": "05_valide_chaabane_karim",
        "scenario": "valide",
        "description": "Dossier complet et cohérent (L1 à L3, génie mécanique).",
        "nom": "CHAABANE", "prenom": "KARIM", "genre": "M",
        "date_naissance": "08/05/2003", "lieu_naissance": "GABES", "cin_numero": "08234519",
        "pere": "ADEL CHAABANE", "mere": "MONIA REKIK",
        "bac_session": "2021", "bac_filiere": "SCIENCES TECHNIQUES", "bac_mention": "PASSABLE",
        "filiere": "GENIE MECANIQUE",
        "licence_specialite": "GENIE MECANIQUE", "licence_annee": "2024",
        "licence_etablissement": "ISET DE GABES",
        "releves": [
            {"niveau": "L1", "annee": "2021/2022", "moyenne": 11.5, "resultat": "VALIDE"},
            {"niveau": "L2", "annee": "2022/2023", "moyenne": 12.0, "resultat": "VALIDE"},
            {"niveau": "L3", "annee": "2023/2024", "moyenne": 12.6, "resultat": "VALIDE"},
        ],
    },
    {
        "id": "06_incoherence_identite_jendoubi_rania",
        "scenario": "incoherence_identite",
        "description": (
            "L'acte de naissance porte le prénom RAYEN au lieu de RANIA : simule un "
            "document mal déposé (ou appartenant à une autre personne). Doit être "
            "signalé par verification/identity_checker.py."
        ),
        "nom": "JENDOUBI", "prenom": "RANIA", "genre": "F",
        "date_naissance": "16/09/2002", "lieu_naissance": "NABEUL", "cin_numero": "06678321",
        "pere": "NABIL JENDOUBI", "mere": "SONIA MEJRI",
        "bac_session": "2020", "bac_filiere": "SCIENCES EXPERIMENTALES", "bac_mention": "BIEN",
        "filiere": "INFORMATIQUE",
        "licence_specialite": "INFORMATIQUE", "licence_annee": "2023",
        "licence_etablissement": "FACULTE DES SCIENCES DE TUNIS",
        "releves": [
            {"niveau": "L1", "annee": "2020/2021", "moyenne": 13.0, "resultat": "VALIDE"},
            {"niveau": "L2", "annee": "2021/2022", "moyenne": 13.4, "resultat": "VALIDE"},
            {"niveau": "L3", "annee": "2022/2023", "moyenne": 13.9, "resultat": "VALIDE"},
        ],
        "acte_naissance_prenom_override": "RAYEN",
    },
    {
        "id": "07_document_manquant_bouazizi_sami",
        "scenario": "document_manquant",
        "description": (
            "L'acte de naissance n'est pas fourni du tout : dossier incomplet, "
            "utile pour tester un futur score de complétude (rapport §9)."
        ),
        "nom": "BOUAZIZI", "prenom": "SAMI", "genre": "M",
        "date_naissance": "21/04/2002", "lieu_naissance": "SFAX", "cin_numero": "07456102",
        "pere": "TAHER BOUAZIZI", "mere": "RIM GUESMI",
        "bac_session": "2020", "bac_filiere": "SCIENCES TECHNIQUES", "bac_mention": "ASSEZ BIEN",
        "filiere": "GENIE CIVIL",
        "licence_specialite": "GENIE CIVIL", "licence_annee": "2023",
        "licence_etablissement": "ENIS SFAX",
        "releves": [
            {"niveau": "L1", "annee": "2020/2021", "moyenne": 11.8, "resultat": "VALIDE"},
            {"niveau": "L2", "annee": "2021/2022", "moyenne": 12.2, "resultat": "VALIDE"},
            {"niveau": "L3", "annee": "2022/2023", "moyenne": 12.9, "resultat": "VALIDE"},
        ],
        "skip_documents": ["acte_naissance"],
    },
    {
        "id": "08_annees_incoherentes_werghi_nadia",
        "scenario": "annees_incoherentes",
        "description": (
            "Le relevé de L2 (2022/2023) manque : la L3 suit directement la L1, un "
            "trou dans le parcours à détecter (rapport §9 : vérification des années "
            "universitaires, doublons/années manquantes)."
        ),
        "nom": "WERGHI", "prenom": "NADIA", "genre": "F",
        "date_naissance": "05/12/2002", "lieu_naissance": "MONASTIR", "cin_numero": "05987234",
        "pere": "FAOUZI WERGHI", "mere": "HELA CHERIF",
        "bac_session": "2021", "bac_filiere": "SCIENCES TECHNIQUES", "bac_mention": "BIEN",
        "filiere": "GENIE ELECTRIQUE",
        "licence_specialite": "GENIE ELECTRIQUE", "licence_annee": "2024",
        "licence_etablissement": "ISET DE MONASTIR",
        "releves": [
            {"niveau": "L1", "annee": "2021/2022", "moyenne": 13.6, "resultat": "VALIDE"},
            {"niveau": "L3", "annee": "2023/2024", "moyenne": 14.1, "resultat": "VALIDE"},
        ],
    },
    {
        "id": "09_dates_incoherentes_fejjari_hedi",
        "scenario": "dates_incoherentes",
        "description": (
            "La date de naissance diffère entre la CIN (22/09/2002) et l'acte de "
            "naissance (12/03/2003) : incohérence que identity_checker.py ne "
            "détecte pas aujourd'hui (il ne compare que nom/prénom, pas les dates) "
            "- utile pour discuter une évolution de la vérification de cohérence."
        ),
        "nom": "FEJJARI", "prenom": "HEDI", "genre": "M",
        "date_naissance": "22/09/2002", "lieu_naissance": "KAIROUAN", "cin_numero": "06345987",
        "pere": "MABROUK FEJJARI", "mere": "AMEL SALHI",
        "bac_session": "2020", "bac_filiere": "SCIENCES DE GESTION", "bac_mention": "ASSEZ BIEN",
        "filiere": "INFORMATIQUE DE GESTION",
        "licence_specialite": "INFORMATIQUE DE GESTION", "licence_annee": "2023",
        "licence_etablissement": "ISG KAIROUAN",
        "releves": [
            {"niveau": "L1", "annee": "2020/2021", "moyenne": 12.1, "resultat": "VALIDE"},
            {"niveau": "L2", "annee": "2021/2022", "moyenne": 12.5, "resultat": "VALIDE"},
            {"niveau": "L3", "annee": "2022/2023", "moyenne": 13.0, "resultat": "VALIDE"},
        ],
        "acte_naissance_date_override": "12/03/2003",
    },
    {
        "id": "10_echec_annee_ayari_emna",
        "scenario": "echec_annee",
        "description": (
            "L2 ajournée (moyenne 8.40, résultat AJOURNE) : le parcours s'arrête là "
            "(pas de L3 fournie), utile pour tester un futur critère de niveau "
            "académique conforme (rapport §9)."
        ),
        "nom": "AYARI", "prenom": "EMNA", "genre": "F",
        "date_naissance": "30/06/2003", "lieu_naissance": "GAFSA", "cin_numero": "07123456",
        "pere": "LOTFI AYARI", "mere": "IMEN KHEMIRI",
        "bac_session": "2021", "bac_filiere": "SCIENCES TECHNIQUES", "bac_mention": "PASSABLE",
        "filiere": "GENIE MECANIQUE",
        "licence_specialite": "GENIE MECANIQUE", "licence_annee": "2024",
        "licence_etablissement": "ISET DE GAFSA",
        "releves": [
            {"niveau": "L1", "annee": "2021/2022", "moyenne": 11.2, "resultat": "VALIDE"},
            {"niveau": "L2", "annee": "2022/2023", "moyenne": 8.4, "resultat": "AJOURNE"},
        ],
    },
    {
        "id": "11_document_duplique_sassi_yassine",
        "scenario": "document_duplique",
        "description": (
            "Le relevé de L2 est déposé deux fois (releve_l2.png et "
            "releve_l2_bis.png, contenu identique) : simule un doublon d'upload, "
            "utile pour tester une future détection de documents dupliqués "
            "(rapport §9)."
        ),
        "nom": "SASSI", "prenom": "YASSINE", "genre": "M",
        "date_naissance": "11/03/2003", "lieu_naissance": "ARIANA", "cin_numero": "08765432",
        "pere": "ANOUAR SASSI", "mere": "DORRA JAOUADI",
        "bac_session": "2021", "bac_filiere": "SCIENCES TECHNIQUES", "bac_mention": "BIEN",
        "filiere": "INFORMATIQUE",
        "licence_specialite": "INFORMATIQUE", "licence_annee": "2024",
        "licence_etablissement": "FACULTE DES SCIENCES DE TUNIS",
        "releves": [
            {"niveau": "L1", "annee": "2021/2022", "moyenne": 13.9, "resultat": "VALIDE"},
            {"niveau": "L2", "annee": "2022/2023", "moyenne": 14.3, "resultat": "VALIDE"},
            {"niveau": "L3", "annee": "2023/2024", "moyenne": 14.7, "resultat": "VALIDE"},
        ],
        "duplicate_documents": ["releve_l2"],
    },
]


def _filiation_line(candidate: dict) -> str:
    lien = "Fille de" if candidate["genre"] == "F" else "Fils de"
    return f"{lien}: {candidate['pere']} et de {candidate['mere']}"


def generate_candidate(candidate: dict, output_dir: Path) -> dict:
    folder = output_dir / candidate["id"]
    folder.mkdir(parents=True, exist_ok=True)
    documents_written = []

    skip = set(candidate.get("skip_documents", []))

    if "cin" not in skip:
        render_text_image(cin_text(
            candidate["nom"], candidate["prenom"], candidate["date_naissance"],
            candidate["lieu_naissance"], candidate["cin_numero"],
        )).save(folder / "cin.png")
        documents_written.append("cin.png")

    if "acte_naissance" not in skip:
        prenom_acte = candidate.get("acte_naissance_prenom_override", candidate["prenom"])
        date_acte = candidate.get("acte_naissance_date_override", candidate["date_naissance"])
        render_text_image(acte_naissance_text(
            candidate["nom"], prenom_acte, date_acte,
            candidate["lieu_naissance"], _filiation_line(candidate),
        )).save(folder / "acte_naissance.png")
        documents_written.append("acte_naissance.png")

    if "bac" not in skip:
        render_text_image(bac_text(
            candidate["nom"], candidate["prenom"], candidate["bac_session"],
            candidate["bac_filiere"], candidate["bac_mention"],
        )).save(folder / "bac.png")
        documents_written.append("bac.png")

    if "diplome_licence" not in skip:
        render_text_image(licence_text(
            candidate["nom"], candidate["prenom"], candidate["licence_specialite"],
            candidate["licence_annee"], candidate["licence_etablissement"],
        )).save(folder / "diplome_licence.png")
        documents_written.append("diplome_licence.png")

    duplicate = set(candidate.get("duplicate_documents", []))
    for releve in candidate["releves"]:
        niveau = releve["niveau"]
        key = f"releve_{niveau.lower()}"
        if key in skip:
            continue
        image = render_text_image(
            releve_text(
                candidate["nom"], candidate["prenom"], niveau, releve["annee"],
                candidate["filiere"], releve["moyenne"], releve["resultat"],
            ),
            height=720,
        )
        filename = f"{key}.png"
        image.save(folder / filename)
        documents_written.append(filename)
        if key in duplicate:
            bis_filename = f"{key}_bis.png"
            image.save(folder / bis_filename)
            documents_written.append(bis_filename)

    return {
        "id": candidate["id"],
        "scenario": candidate["scenario"],
        "description": candidate["description"],
        "nom_complet": f"{candidate['nom']} {candidate['prenom']}",
        "filiere": candidate["filiere"],
        "dossier": str(folder.relative_to(output_dir.parent.parent)).replace("\\", "/"),
        "documents": documents_written,
    }


def generate_dataset(output_dir: Path = OUTPUT_DIR) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = [generate_candidate(candidate, output_dir) for candidate in CANDIDATES]
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    entries = generate_dataset()
    for entry in entries:
        print(f"{entry['id']:45s} [{entry['scenario']:>22s}]  {len(entry['documents'])} document(s)")
    print(f"\n{len(entries)} dossiers générés dans {OUTPUT_DIR}")
