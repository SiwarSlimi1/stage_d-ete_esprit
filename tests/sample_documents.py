"""Génère un jeu de documents synthétiques (rapport §7.2) faute de scans réels
disponibles pour ce POC. Le texte est rendu sous forme d'image, ce qui permet de
valider la chaîne complète prétraitement -> OCR -> classification -> extraction.

Usage : python -m tests.sample_documents
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config.settings import SAMPLES_DIR

FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
FONT_SIZE = 28

SAMPLE_TEXTS = {
    "cin": """REPUBLIQUE TUNISIENNE
CARTE D'IDENTITE NATIONALE

Nom: BEN ALI
Prenom: SALMA
Date de naissance: 12/04/2001
Lieu de naissance: TUNIS
Nationalite: TUNISIENNE
N CIN: 08453219""",
    "acte_naissance": """REPUBLIQUE TUNISIENNE
ACTE DE NAISSANCE
Extrait du registre de l'etat civil

Nom: BEN ALI
Prenom: SALMA
Date de naissance: 12/04/2001
Lieu de naissance: TUNIS
Fille de: MOHAMED BEN ALI et de FATMA TRABELSI""",
    "bac": """REPUBLIQUE TUNISIENNE
MINISTERE DE L'EDUCATION
DIPLOME DU BACCALAUREAT

Nom: BEN ALI
Prenom: SALMA
Session: 2019
Filiere: SCIENCES INFORMATIQUES
Mention: ASSEZ BIEN""",
    "diplome_licence": """REPUBLIQUE TUNISIENNE
MINISTERE DE L'ENSEIGNEMENT SUPERIEUR
DIPLOME NATIONAL DE LICENCE

Nom: BEN ALI
Prenom: SALMA
Specialite: INFORMATIQUE DE GESTION
Annee d'obtention: 2024
Etablissement: FACULTE DES SCIENCES DE TUNIS""",
    "releve_notes": """RELEVE DE NOTES
Annee universitaire: 2022/2023
Etudiant: BEN ALI SALMA

Algorithmique: 14.5
Bases de donnees: 13.0
Reseaux: 15.0

Moyenne generale: 14.16
Resultat: VALIDE""",
}


def render_text_image(text: str, width: int = 900, height: int = 650) -> Image.Image:
    """Rend un bloc de texte sous forme d'image en niveaux de gris (fond blanc)."""
    image = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except OSError:
        font = ImageFont.load_default()
    draw.multiline_text((40, 40), text, fill=0, font=font, spacing=14)
    return image


def generate_sample_documents(output_dir: Path = SAMPLES_DIR) -> dict[str, Path]:
    """Génère les 5 images d'exemple et retourne {document_type: chemin_fichier}."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for doc_type, text in SAMPLE_TEXTS.items():
        image = render_text_image(text)
        path = output_dir / f"{doc_type}.png"
        image.save(path)
        paths[doc_type] = path
    return paths


if __name__ == "__main__":
    generated = generate_sample_documents()
    for doc_type, path in generated.items():
        print(f"{doc_type}: {path}")
