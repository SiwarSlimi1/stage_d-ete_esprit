"""Éléments d'interface partagés entre l'espace enseignant (app.py) et l'espace
candidat (pages/1_Espace_Candidat.py) : thème visuel ESPRIT, emplacements de
documents, exécution mise en cache du pipeline, sélecteur de fournisseur LLM.
"""
import base64
import json
import os
import tempfile
from pathlib import Path

import streamlit as st

from config.settings import SAMPLES_DIR
from main import process_document
from ocr.tesseract_engine import extract_text
from preprocessing.image_utils import load_image, preprocess_pipeline

ESPRIT_RED = "#c1272d"
LOGO_PATH = Path(__file__).parent / "assets" / "logo_esprit.png"

STATUS_LABELS = {
    "success": ("🟢", "Complet", "status-ok"),
    "partial": ("🟡", "À vérifier manuellement", "status-warn"),
    "failed": ("🔴", "Incomplet", "status-bad"),
}

DOCUMENT_SLOTS = [
    {"key": "cin", "label": "Carte d'identité nationale (CIN)", "sample_prefix": "cin"},
    {"key": "acte_naissance", "label": "Acte de naissance", "sample_prefix": "acte_naissance"},
    {"key": "bac", "label": "Diplôme du baccalauréat", "sample_prefix": "bac"},
    {"key": "diplome_licence", "label": "Diplôme de licence", "sample_prefix": "diplome_licence"},
    {"key": "releve_notes", "label": "Relevé de notes", "sample_prefix": "releve_notes"},
]


def _logo_data_uri() -> str | None:
    if not LOGO_PATH.exists():
        return None
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def inject_esprit_theme(title_main: str, title_sub: str) -> None:
    """Injecte le CSS et l'en-tête ESPRIT communs. À appeler une fois en tête de
    chaque page (juste après st.set_page_config)."""
    logo_uri = _logo_data_uri()
    logo_html = (
        f'<img src="{logo_uri}" alt="ESPRIT" />'
        if logo_uri
        else 'espr<span class="accent">it</span> <span class="accent">▸</span>'
    )

    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: #e4e4e5; }}
        section.main > div.block-container {{
            background: #ffffff; border-radius: 6px; padding: 2rem 2.5rem 2.5rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.12); max-width: 1180px;
        }}
        .esprit-header {{
            display: flex; align-items: center; justify-content: space-between;
            border-bottom: 3px solid {ESPRIT_RED}; padding-bottom: 0.9rem; margin-bottom: 1.4rem;
        }}
        .esprit-logo img {{ height: 54px; }}
        .esprit-logo {{ font-size: 1.9rem; font-weight: 800; color: #1a1a1a; letter-spacing: -0.5px; }}
        .esprit-logo .accent {{ color: {ESPRIT_RED}; }}
        .esprit-title {{ text-align: right; }}
        .esprit-title .main {{ color: {ESPRIT_RED}; font-weight: 700; font-size: 1.05rem; }}
        .esprit-title .sub {{ color: #666; font-size: 0.8rem; }}
        .doc-card {{
            border: 1px solid #e0e0e0; border-radius: 6px; padding: 1.1rem 1.3rem;
            margin-bottom: 1.3rem; background: #fbfbfb;
        }}
        .doc-card h4 {{ margin-top: 0; color: #1a1a1a; }}
        .status-ok {{ color: #1e7a34; font-weight: 700; }}
        .status-warn {{ color: #8a5a00; font-weight: 700; }}
        .status-bad {{ color: #b3261e; font-weight: 700; }}
        .mismatch-banner {{
            background: #fdecea; border: 1px solid {ESPRIT_RED}; color: #7a1a1a;
            border-radius: 4px; padding: 0.6rem 0.9rem; margin-bottom: 0.8rem; font-size: 0.9rem;
        }}
        .quiz-question {{
            border: 1px solid #e0e0e0; border-radius: 6px; padding: 1rem 1.2rem;
            margin-bottom: 1rem; background: #fbfbfb;
        }}
        div.stButton > button {{ background-color: {ESPRIT_RED}; color: white; border: none; }}
        div.stButton > button:hover {{ background-color: #9c1f24; color: white; }}
        </style>

        <div class="esprit-header">
          <div class="esprit-logo">{logo_html}</div>
          <div class="esprit-title">
            <div class="main">{title_main}</div>
            <div class="sub">{title_sub}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def run_pipeline(file_bytes: bytes, suffix: str) -> dict:
    """Exécute le pipeline complet sur des octets d'image et met le résultat en
    cache (par contenu) pour ne pas retraiter un document déjà vu à chaque
    interaction avec un autre champ du dossier."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(file_bytes)
    tmp.close()
    path = Path(tmp.name)
    processed_image = preprocess_pipeline(load_image(path))
    raw_text = extract_text(processed_image)
    result = process_document(path)
    return {"path": path, "processed_image": processed_image, "raw_text": raw_text, "result": result}


def find_sample(prefix: str) -> Path | None:
    """Cherche un document d'exemple pour ce préfixe. Les documents synthétiques
    (.png) sont préférés aux vraies photos (.jpg) pour garder une identité
    cohérente sur l'ensemble du dossier de démonstration ; les vraies photos
    restent testables individuellement via "Téléverser mes documents"."""
    candidates = sorted(SAMPLES_DIR.glob(f"{prefix}.*"), key=lambda p: (p.suffix.lower() != ".png", p.name))
    return candidates[0] if candidates else None


def render_document_card(slot: dict, path: Path, processed_image, raw_text: str, result: dict) -> None:
    icon, status_label, status_css = STATUS_LABELS.get(
        result["extraction_status"], ("⚪", result["extraction_status"], "")
    )

    st.markdown('<div class="doc-card">', unsafe_allow_html=True)
    st.markdown(f"#### {slot['label']}")

    if result["document_type"] != slot["key"] and result["document_type"] != "inconnu":
        st.markdown(
            f'<div class="mismatch-banner">⚠️ Ce document a été classé comme '
            f'<code>{result["document_type"]}</code> par le système, alors qu\'il a été déposé dans '
            f'l\'emplacement « {slot["label"]} ». Vérifier qu\'il ne s\'agit pas d\'une erreur de dépôt '
            f'(rapport §2.2.5, documents mal catégorisés).</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<span class="{status_css}">{icon} {status_label}</span> — '
        f'type détecté : <code>{result["document_type"]}</code> — '
        f'confiance {result["classification_confidence"]:.0%}',
        unsafe_allow_html=True,
    )

    col_image, col_fields = st.columns([1, 1.4])
    with col_image:
        st.image(str(path), use_container_width=True)

    with col_fields:
        if result["fields"]:
            rows = [
                {"champ": k, "valeur": json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v}
                for k, v in result["fields"].items()
            ]
            st.table(rows)
        else:
            st.write("Aucun champ extrait.")

        if result["missing_fields"]:
            st.error("Champs manquants : " + ", ".join(result["missing_fields"]))

        if result["warnings"]:
            for warning in result["warnings"]:
                st.warning(warning)

    with st.expander("Rapport JSON complet"):
        st.json(result)
    with st.expander("Image prétraitée transmise à l'OCR"):
        st.image(processed_image, use_container_width=True, clamp=True)
    with st.expander("Texte OCR brut"):
        st.text(raw_text or "(aucun texte détecté)")

    st.markdown("</div>", unsafe_allow_html=True)


def llm_provider_selector(key_prefix: str) -> tuple[str, str | None]:
    """Sélecteur de fournisseur LLM + champ de clé API, réutilisé par l'espace
    enseignant (questions d'entretien) et l'espace candidat (quiz). Retourne
    (provider, api_key)."""
    col_provider, col_key = st.columns([1, 2])
    with col_provider:
        provider_choice = st.selectbox(
            "Fournisseur LLM",
            ["Google Gemini (gratuit)", "OpenAI"],
            help="Gemini propose un palier gratuit sans carte bancaire via Google AI Studio "
            "(aistudio.google.com/apikey) - recommandé pour tester ce module.",
            key=f"{key_prefix}_provider",
        )
    provider = "gemini" if provider_choice.startswith("Google") else "openai"
    env_var = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"

    with col_key:
        api_key_input = st.text_input(
            f"Clé API ({provider_choice})",
            value=os.environ.get(env_var, ""),
            type="password",
            help="Jamais enregistrée sur le disque : utilisée uniquement pour cette session.",
            key=f"{key_prefix}_api_key",
        )
    return provider, (api_key_input or None)
