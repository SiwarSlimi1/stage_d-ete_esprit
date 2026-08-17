"""Génère les images de tout un dataset de dossiers synthétiques (JSON) en
réutilisant la même logique de rendu que tests/sample_documents.py (rapport §7.2).

Contrairement à sample_documents.py (5 images fixes, un seul dossier "BEN ALI
SALMA"), ce script prend en entrée un fichier JSON contenant N dossiers
(cf. dossiers_synthetiques_esprit_1000.json) et génère, pour chaque dossier,
une image par document réellement présent (le champ "bac" peut être absent,
cf. anomalie "document_bac_manquant") ainsi qu'une image par relevé de notes
(un relevé = un document physique par année universitaire : L1, L2, L3, M1).

Le texte rendu suit strictement le format "Label: valeur" attendu en priorité
par extraction.base_extractor.extract_after_label et par les mots-clés de
classification.rules_classifier, afin que le round-trip OCR -> classification
-> extraction fonctionne exactement comme sur les 5 échantillons historiques.

Usage :
    python -m tests.generate_dataset_images --input chemin/vers/dossiers.json \
        --output data/samples_dataset --limit 50

Sans --limit, les dossiers du fichier sont tous traités.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config.settings import DATA_DIR

# Même police que sample_documents.py (Windows), avec repli multiplateforme
# (DejaVu Sans sur Linux/Mac, puis police bitmap par défaut de Pillow en
# dernier recours) pour que le script tourne aussi bien sur le poste de
# développement que dans un environnement CI/Linux.
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
FONT_SIZE = 28

DEFAULT_OUTPUT_DIR = DATA_DIR / "samples_dataset"


def _load_font() -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, FONT_SIZE)
    return ImageFont.load_default()


def render_text_image(text: str, width: int | None = None, height: int | None = None) -> Image.Image:
    """Rend un bloc de texte sous forme d'image en niveaux de gris (fond blanc).

    Identique à sample_documents.render_text_image, avec une hauteur calculée
    automatiquement lorsque le texte est plus long que les 5 échantillons
    d'origine (cas des relevés de notes, qui comptent jusqu'à 7 matières), et une
    largeur calculée automatiquement à partir de la ligne la plus longue : une
    largeur fixe à 900px rognait silencieusement la fin des valeurs longues (ex.
    "Institut Superieur des Etudes Technologiques de Sousse"), rendant ce champ
    illisible même par un humain, pas seulement par l'OCR.
    """
    font = _load_font()
    lines = text.split("\n")
    if width is None:
        measurer = ImageDraw.Draw(Image.new("L", (1, 1)))
        max_line_width = max((measurer.textlength(line, font=font) for line in lines), default=0)
        width = max(900, int(max_line_width) + 80)
    if height is None:
        height = max(400, 40 * 2 + len(lines) * (FONT_SIZE + 14))
    image = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(image)
    draw.multiline_text((40, 40), text, fill=0, font=font, spacing=14)
    return image


# --------------------------------------------------------------------------
# Construction du texte "Label: valeur" par type de document, à partir d'un
# enregistrement du JSON (mêmes clés que le contrat défini dans le prompt de
# génération de données : cf. dossiers_synthetiques_esprit_1000_manifest.json)
# --------------------------------------------------------------------------


def _cin_text(d: dict) -> str:
    c = d["cin"]
    return (
        "REPUBLIQUE TUNISIENNE\n"
        "CARTE D'IDENTITE NATIONALE\n\n"
        f"Nom: {c['nom']}\n"
        f"Prenom: {c['prenom']}\n"
        f"Date de naissance: {c['date_naissance']}\n"
        f"Lieu de naissance: {c['lieu_naissance']}\n"
        "Nationalite: TUNISIENNE\n"
        f"N CIN: {c['numero_document']}"
    )


def _acte_naissance_text(d: dict) -> str:
    a = d["acte_naissance"]
    # "Ne de" matche le même motif que "Né de" une fois normalisé (accents
    # retirés), cf. extraction.acte_naissance_extractor._extract_filiation.
    return (
        "REPUBLIQUE TUNISIENNE\n"
        "ACTE DE NAISSANCE\n"
        "Extrait du registre de l'etat civil\n\n"
        f"Nom: {a['nom']}\n"
        f"Prenom: {a['prenom']}\n"
        f"Date de naissance: {a['date_naissance']}\n"
        f"Lieu de naissance: {a['lieu_naissance']}\n"
        f"Ne de: {a['nom_pere']} et de {a['nom_mere']}"
    )


def _bac_text(d: dict) -> str:
    b = d["bac"]
    return (
        "REPUBLIQUE TUNISIENNE\n"
        "MINISTERE DE L'EDUCATION\n"
        "DIPLOME DU BACCALAUREAT\n\n"
        f"Nom: {b['nom']}\n"
        f"Prenom: {b['prenom']}\n"
        f"Session: {b['annee_obtention']}\n"
        f"Filiere: {b['serie']}\n"
        f"Mention: {b['mention']}"
    )


def _licence_text(d: dict) -> str:
    lic = d["diplome_licence"]
    return (
        "REPUBLIQUE TUNISIENNE\n"
        "MINISTERE DE L'ENSEIGNEMENT SUPERIEUR\n"
        "DIPLOME NATIONAL DE LICENCE\n\n"
        f"Nom: {lic['nom']}\n"
        f"Prenom: {lic['prenom']}\n"
        f"Specialite: {lic['specialite']}\n"
        f"Annee d'obtention: {lic['annee_obtention']}\n"
        f"Etablissement: {lic['etablissement']}"
    )


def _releve_text(releve: dict) -> str:
    # Une matière par ligne au format "Matiere: note" (sans le coefficient,
    # non reconnu par extraction.releve_extractor._extract_matieres).
    matieres_lines = "\n".join(f"{m['matiere']}: {m['note']:.2f}" for m in releve["matieres"])
    resultat = "VALIDE" if releve["moyenne"] >= 10 else "AJOURNE"
    return (
        "RELEVE DE NOTES\n"
        f"Annee universitaire: {releve['annee_universitaire']}\n"
        f"Niveau: {releve['niveau']}\n"
        f"Etudiant: {releve['nom_complet']}\n\n"
        f"{matieres_lines}\n\n"
        f"Moyenne generale: {releve['moyenne']:.2f}\n"
        f"Resultat: {resultat}"
    )


def generate_dossier_images(dossier: dict, dossier_dir: Path) -> dict[str, Path]:
    """Génère les images d'un seul dossier et retourne {nom_fichier: chemin}."""
    dossier_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    builders = {
        "cin": _cin_text,
        "acte_naissance": _acte_naissance_text,
        "bac": _bac_text,
        "diplome_licence": _licence_text,
    }
    for doc_type, builder in builders.items():
        if doc_type not in dossier:
            continue  # ex. anomalie "document_bac_manquant"
        image = render_text_image(builder(dossier))
        path = dossier_dir / f"{doc_type}.png"
        image.save(path)
        paths[doc_type] = path

    for releve in dossier.get("releve_notes", []):
        image = render_text_image(_releve_text(releve))
        path = dossier_dir / f"releve_{releve['niveau']}.png"
        image.save(path)
        paths[f"releve_{releve['niveau']}"] = path

    return paths


def generate_dataset(
    input_json: Path, output_dir: Path = DEFAULT_OUTPUT_DIR, limit: int | None = None
) -> Path:
    """Génère les images de tout le dataset et écrit un manifest.jsonl associant
    chaque dossier généré à ses données de vérité terrain (ground truth), utile
    pour évaluer automatiquement la sortie du pipeline OCR/extraction.
    """
    with open(input_json, encoding="utf-8") as f:
        dossiers = json.load(f)
    if limit is not None:
        dossiers = dossiers[:limit]

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.jsonl"

    with open(manifest_path, "w", encoding="utf-8") as manifest_file:
        for index, dossier in enumerate(dossiers):
            anomalie = dossier.get("_anomalie", "coherent")
            dossier_dir = output_dir / f"{index:04d}_{anomalie}"
            generated = generate_dossier_images(dossier, dossier_dir)

            manifest_entry = {
                "dossier_index": index,
                "dossier_dir": str(dossier_dir.relative_to(output_dir)),
                "anomalie": anomalie,
                "fichiers_generes": {k: str(v.name) for k, v in generated.items()},
                "ground_truth": dossier,
            }
            manifest_file.write(json.dumps(manifest_entry, ensure_ascii=False) + "\n")

            if (index + 1) % 50 == 0:
                print(f"{index + 1} dossiers generes...")

    print(f"Termine : {len(dossiers)} dossiers generes dans {output_dir}")
    print(f"Manifest (verite terrain) : {manifest_path}")
    return manifest_path


def regenerate_from_manifest(dataset_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    """Re-rend les images d'un dataset déjà généré, à partir de la vérité terrain
    déjà présente dans son manifest.jsonl - sans avoir besoin du fichier JSON
    d'origine (ex. dossiers_synthetiques_esprit_1000.json, pas forcément
    disponible). Utile après une correction de rendu (ex. largeur de canevas
    fixe à 900px qui rognait les valeurs longues comme un nom d'établissement)."""
    manifest_path = dataset_dir / "manifest.jsonl"
    with open(manifest_path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]

    print(f"Regeneration de {len(entries)} dossiers depuis {manifest_path}...")
    for index, entry in enumerate(entries):
        generate_dossier_images(entry["ground_truth"], dataset_dir / entry["dossier_dir"])
        if (index + 1) % 100 == 0:
            print(f"  {index + 1}/{len(entries)}")
    print("Termine.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Fichier JSON des dossiers (dataset complet)")
    parser.add_argument(
        "--from-manifest", action="store_true",
        help="Re-rendre les images d'un dataset existant depuis son manifest.jsonl (voir --output)",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Dossier de sortie des images"
    )
    parser.add_argument("--limit", type=int, default=None, help="Nombre de dossiers a generer (defaut: tous)")
    args = parser.parse_args()
    if not args.input and not args.from_manifest:
        parser.error("préciser --input <fichier.json> ou --from-manifest")
    return args


if __name__ == "__main__":
    args = _parse_args()
    if args.from_manifest:
        regenerate_from_manifest(args.output)
    else:
        generate_dataset(args.input, args.output, args.limit)
