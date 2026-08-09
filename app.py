"""Interface Streamlit de démonstration du pipeline Sprint 1 & 2.

    prétraitement (OpenCV) -> OCR (Tesseract) -> classification (règles) -> extraction

Usage : streamlit run app.py

Ce système n'émet aucune décision d'admission (rapport §1.5) : il produit un
rapport de vérification destiné à assister les enseignants.
"""
import json
import tempfile
from pathlib import Path

import streamlit as st

from config.settings import SAMPLES_DIR
from main import process_document
from ocr.tesseract_engine import extract_text
from preprocessing.image_utils import load_image, preprocess_pipeline

st.set_page_config(page_title="POC Vérification IA — ESPRIT", page_icon="📄", layout="wide")

STATUS_LABELS = {
    "success": ("🟢", "Complet"),
    "partial": ("🟡", "À vérifier manuellement"),
    "failed": ("🔴", "Incomplet"),
}

st.title("📄 POC Vérification IA des dossiers d'admission — ESPRIT")
st.caption("Prétraitement OpenCV → OCR Tesseract → Classification par règles → Extraction structurée")
st.info(
    "Ce système n'émet **aucune décision d'admission** : il produit un rapport de "
    "vérification destiné à assister les enseignants (rapport de stage, §1.5)."
)

source = st.radio("Source du document", ["Téléverser une image", "Utiliser un exemple"], horizontal=True)

image_path: Path | None = None

if source == "Téléverser une image":
    uploaded = st.file_uploader(
        "Document (CIN, acte de naissance, bac, licence, relevé de notes)",
        type=["png", "jpg", "jpeg"],
    )
    if uploaded is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded.name).suffix)
        tmp.write(uploaded.getbuffer())
        tmp.close()
        image_path = Path(tmp.name)
else:
    samples = sorted(SAMPLES_DIR.glob("*.png")) + sorted(SAMPLES_DIR.glob("*.jpg")) + sorted(SAMPLES_DIR.glob("*.jpeg"))
    if samples:
        image_path = st.selectbox("Exemple disponible dans data/samples/", samples, format_func=lambda p: p.name)
    else:
        st.warning("Aucun exemple trouvé dans data/samples/. Lancez `python -m tests.sample_documents`.")

if image_path is not None:
    col_original, col_processed = st.columns(2)
    with col_original:
        st.subheader("Document source")
        st.image(str(image_path), use_container_width=True)

    with st.spinner("Traitement en cours (prétraitement → OCR → classification → extraction)…"):
        processed_image = preprocess_pipeline(load_image(image_path))
        raw_text = extract_text(processed_image)
        result = process_document(image_path)

    with col_processed:
        st.subheader("Image transmise à l'OCR (après prétraitement)")
        st.image(processed_image, use_container_width=True, clamp=True)

    st.divider()

    icon, status_label = STATUS_LABELS.get(result["extraction_status"], ("⚪", result["extraction_status"]))
    st.subheader(
        f"{icon} Type détecté : `{result['document_type']}` "
        f"— confiance {result['classification_confidence']:.0%} — statut : {status_label}"
    )

    col_fields, col_json = st.columns([1, 1])

    with col_fields:
        st.markdown("**Champs extraits**")
        if result["fields"]:
            rows = [
                {"champ": k, "valeur": json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v}
                for k, v in result["fields"].items()
            ]
            st.table(rows)
        else:
            st.write("Aucun champ extrait.")

        if result["missing_fields"]:
            st.markdown("**Champs manquants**")
            st.error(", ".join(result["missing_fields"]))

        if result["warnings"]:
            st.markdown("**Avertissements**")
            for warning in result["warnings"]:
                st.warning(warning)

    with col_json:
        st.markdown("**Rapport JSON (contrat commun, rapport §3.2.4)**")
        st.json(result)

    with st.expander("Texte OCR brut"):
        st.text(raw_text or "(aucun texte détecté)")
