"""Interface Streamlit de démonstration du pipeline Sprint 1 & 2.

    prétraitement (OpenCV) -> OCR (Tesseract) -> classification (règles) -> extraction

Usage : streamlit run app.py

Ce système n'émet aucune décision d'admission (rapport §1.5) : il produit un
rapport de vérification destiné à assister les enseignants. Chaque type de
document du dossier (CIN, acte de naissance, bac, licence, relevé de notes) a
son propre emplacement de dépôt, à l'image d'un vrai dossier de candidature.
"""
import base64
import json
import os
import tempfile
from pathlib import Path

import streamlit as st

from config.settings import SAMPLES_DIR
from interview.question_generator import LLMNotConfiguredError, build_candidate_profile, generate_interview_questions
from main import process_document
from ocr.tesseract_engine import extract_text
from preprocessing.image_utils import load_image, preprocess_pipeline
from verification.identity_checker import check_identity_consistency

st.set_page_config(page_title="POC Vérification IA — ESPRIT", page_icon="📄", layout="wide")

ESPRIT_RED = "#c1272d"
LOGO_PATH = Path(__file__).parent / "assets" / "logo_esprit.png"


def _logo_data_uri() -> str | None:
    if not LOGO_PATH.exists():
        return None
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"

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

# ---------- Thème visuel inspiré de l'identité ESPRIT (rouge/blanc/gris) ----------
_logo_uri = _logo_data_uri()
logo_html = (
    f'<img src="{_logo_uri}" alt="ESPRIT" />'
    if _logo_uri
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
    div.stButton > button {{ background-color: {ESPRIT_RED}; color: white; border: none; }}
    div.stButton > button:hover {{ background-color: #9c1f24; color: white; }}
    </style>

    <div class="esprit-header">
      <div class="esprit-logo">{logo_html}</div>
      <div class="esprit-title">
        <div class="main">POC Vérification IA des dossiers d'admission</div>
        <div class="sub">Outil interne de test — Admission parallèle 2025/2026</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Ce système n'émet **aucune décision d'admission** : il produit un rapport de "
    "vérification destiné à assister les enseignants (rapport de stage, §1.5)."
)


@st.cache_data(show_spinner=False)
def _run_pipeline(file_bytes: bytes, suffix: str) -> dict:
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


def _find_sample(prefix: str) -> Path | None:
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

    st.markdown(f'<div class="doc-card">', unsafe_allow_html=True)
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


mode = st.radio(
    "Source des documents du dossier",
    ["Téléverser mes documents", "Utiliser les documents d'exemple"],
    horizontal=True,
)

st.divider()

filled_results: list[dict] = []

for slot in DOCUMENT_SLOTS:
    path: Path | None = None
    processed_image = raw_text = result = None

    if mode == "Utiliser les documents d'exemple":
        sample_path = _find_sample(slot["sample_prefix"])
        if sample_path is not None:
            with st.spinner(f"Traitement — {slot['label']}…"):
                data = _run_pipeline(sample_path.read_bytes(), sample_path.suffix)
            # Le document affiché et le "source_image" du rapport doivent pointer
            # vers le fichier d'exemple d'origine, pas vers la copie temporaire
            # utilisée en interne pour le traitement.
            path = sample_path
            processed_image, raw_text = data["processed_image"], data["raw_text"]
            result = {**data["result"], "source_image": str(sample_path)}
    else:
        uploaded = st.file_uploader(
            f"Déposer : {slot['label']}", type=["png", "jpg", "jpeg"], key=f"upload_{slot['key']}"
        )
        if uploaded is not None:
            with st.spinner(f"Traitement — {slot['label']}…"):
                data = _run_pipeline(uploaded.getvalue(), Path(uploaded.name).suffix)
            path, processed_image, raw_text, result = (
                data["path"],
                data["processed_image"],
                data["raw_text"],
                data["result"],
            )

    if result is not None:
        render_document_card(slot, path, processed_image, raw_text, result)
        filled_results.append({"slot": slot, "result": result})
    else:
        st.markdown(f"##### {slot['label']}")
        st.caption("Aucun document déposé pour ce champ.")
        st.markdown("<hr style='border-top:1px solid #ededed; margin: 0.6rem 0 1.2rem;'>", unsafe_allow_html=True)

# ---------- Vérification de cohérence d'identité (rapport §2.2.4, §3.2.5) ----------
st.divider()
st.markdown("### Cohérence d'identité entre documents")

identity_documents = [
    {"label": item["slot"]["label"], "fields": item["result"]["fields"]} for item in filled_results
]
identity_result = check_identity_consistency(identity_documents)

if identity_result["comparable_documents"] < 2:
    st.caption("Pas encore assez de documents avec un nom/prénom exploitable pour comparer.")
elif identity_result["consistent"]:
    st.success(
        f"✅ Identité cohérente sur les {identity_result['comparable_documents']} "
        "documents comparés."
    )
else:
    st.error("🚫 Incohérence d'identité détectée entre plusieurs documents du dossier :")
    for issue in identity_result["issues"]:
        st.markdown(f"- {issue}")
    st.caption(
        "Le système signale l'anomalie mais ne rejette jamais automatiquement un "
        "dossier — la décision reste aux enseignants (rapport §1.5). La génération "
        "des questions d'entretien est toutefois bloquée tant que l'incohérence "
        "n'est pas résolue."
    )

# ---------- Aperçu du dossier ----------
st.divider()
st.markdown("### Aperçu du dossier")

nb_total = len(DOCUMENT_SLOTS)
nb_fournis = len(filled_results)
nb_success = sum(1 for r in filled_results if r["result"]["extraction_status"] == "success")
nb_mismatch = sum(
    1 for r in filled_results
    if r["result"]["document_type"] != r["slot"]["key"] and r["result"]["document_type"] != "inconnu"
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Documents fournis", f"{nb_fournis} / {nb_total}")
col2.metric("Extractions complètes", f"{nb_success} / {nb_fournis}" if nb_fournis else "0 / 0")
col3.metric("Documents mal catégorisés", nb_mismatch)
col4.metric("Identité cohérente", "Oui" if identity_result["consistent"] else "Non")

st.caption(
    "Cet aperçu ne remplace pas le score de complétude officiel (années "
    "universitaires, niveau académique) qui relève de la suite du Sprint 3, non "
    "encore implémentée."
)

# ---------- Questions d'entretien (Module 2, rapport §3.3) ----------
st.divider()
st.markdown("### Questions d'entretien (Module 2)")
st.caption(
    "Génère des questions adaptées au profil du candidat (spécialité, résultats, "
    "matières les mieux évaluées) à l'aide d'un LLM externe. Ce module n'intervient "
    "jamais dans la vérification documentaire ci-dessus (rapport §4.5)."
)

api_key_input = st.text_input(
    "Clé API LLM (OpenAI)",
    value=os.environ.get("OPENAI_API_KEY", ""),
    type="password",
    help="Jamais enregistrée sur le disque : utilisée uniquement pour cette session.",
)
nb_questions = st.number_input("Nombre de questions à générer", min_value=5, max_value=50, value=30, step=5)

can_generate = bool(filled_results) and identity_result["consistent"]
if not filled_results:
    st.caption("Dépose au moins un document du dossier pour générer des questions.")
elif not identity_result["consistent"]:
    st.caption("Génération bloquée : résous l'incohérence d'identité ci-dessus avant de continuer.")

if st.button("Générer les questions d'entretien", disabled=not can_generate):
    documents_for_profile = [
        {"document_type": item["result"]["document_type"], "fields": item["result"]["fields"]}
        for item in filled_results
    ]
    profile = build_candidate_profile(documents_for_profile)

    with st.expander("Profil candidat transmis au LLM"):
        st.json(profile)

    try:
        with st.spinner("Génération des questions en cours…"):
            questions = generate_interview_questions(
                profile, nb_questions=int(nb_questions), api_key=api_key_input or None
            )
        for i, question in enumerate(questions, start=1):
            st.markdown(f"**{i}.** {question}")
    except LLMNotConfiguredError as exc:
        st.warning(str(exc))
    except ImportError:
        st.warning(
            "Le paquet `openai` n'est pas installé. Lancez `pip install openai` "
            "dans l'environnement du projet."
        )
    except Exception as exc:  # noqa: BLE001 - affichage direct de l'erreur API pour le debug en démo
        st.error(f"Échec de l'appel au LLM : {exc}")
