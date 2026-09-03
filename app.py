"""Interface Streamlit — Espace enseignant (vérification des dossiers).

    prétraitement (OpenCV) -> OCR (Tesseract) -> classification (règles) -> extraction

Usage : streamlit run app.py

Ce système n'émet aucune décision d'admission (rapport §1.5) : il produit un
rapport de vérification destiné à assister les enseignants. Chaque type de
document du dossier (CIN, acte de naissance, bac, licence, relevé de notes) a
son propre emplacement de dépôt, à l'image d'un vrai dossier de candidature.

Voir aussi pages/1_Espace_Candidat.py : espace séparé où le candidat s'entraîne
avec un quiz de pré-entretien généré à partir de son profil (demandé par
l'encadrante), dont le score est visible ci-dessous une fois complété.
"""
from pathlib import Path

import streamlit as st

from config.settings import (
    COMPLETENESS_WEIGHT_COHERENCE,
    COMPLETENESS_WEIGHT_EXTRACTION,
    COMPLETENESS_WEIGHT_PRESENCE,
)
from interview.question_generator import LLMNotConfiguredError, build_candidate_profile, generate_interview_questions
from interview.quiz_store import candidate_key, load as load_candidate_data, save_profile
from ui_common import (
    COMPLETENESS_STATUS_LABELS,
    DOCUMENT_SLOTS,
    SCENARIO_ICONS,
    demo_document_slots,
    find_sample,
    inject_esprit_theme,
    llm_provider_selector,
    load_demo_dataset,
    render_document_card,
    run_pipeline,
)
from verification.academic_years_checker import check_academic_years
from verification.completeness_score import compute_completeness
from verification.duplicate_document_checker import check_duplicate_documents
from verification.identity_checker import check_identity_consistency

st.set_page_config(page_title="POC Vérification IA — ESPRIT", page_icon="📄", layout="wide")
inject_esprit_theme(
    "POC Vérification IA des dossiers d'admission",
    "Espace enseignant — Admission parallèle 2025/2026",
)

st.info(
    "Ce système n'émet **aucune décision d'admission** : il produit un rapport de "
    "vérification destiné à assister les enseignants (rapport de stage, §1.5)."
)

MODE_UPLOAD = "Téléverser mes documents"
MODE_SAMPLE = "Utiliser les documents d'exemple"
MODE_DEMO = "Dossier de démonstration (jeu de données synthétique)"

mode = st.radio("Source des documents du dossier", [MODE_UPLOAD, MODE_SAMPLE, MODE_DEMO], horizontal=True)

demo_entry: dict | None = None
active_slots = DOCUMENT_SLOTS

if mode == MODE_DEMO:
    demo_dataset = load_demo_dataset()
    if not demo_dataset:
        st.warning(
            "Aucun dossier de démonstration trouvé. Génère-les d'abord avec "
            "`python -m tests.generate_synthetic_dataset` (voir "
            "`data/dossiers_synthetiques/README.md`)."
        )
    else:
        demo_entry = st.selectbox(
            "Dossier candidat (100% synthétique — aucune donnée réelle, rapport §10)",
            demo_dataset,
            format_func=lambda e: f"{SCENARIO_ICONS.get(e['scenario'], '•')} {e['nom_complet']} — {e['filiere'].title()}",
        )
        st.caption(demo_entry["description"])
        active_slots = demo_document_slots(demo_entry)

st.divider()

filled_results: list[dict] = []

for slot in active_slots:
    path: Path | None = None
    processed_image = raw_text = result = None

    if mode == MODE_DEMO:
        if demo_entry is not None and slot["path"] is not None:
            with st.spinner(f"Traitement — {slot['label']}…"):
                data = run_pipeline(slot["path"].read_bytes(), slot["path"].suffix)
            path = slot["path"]
            processed_image, raw_text = data["processed_image"], data["raw_text"]
            result = {**data["result"], "source_image": str(path)}
    elif mode == MODE_SAMPLE:
        sample_path = find_sample(slot["sample_prefix"])
        if sample_path is not None:
            with st.spinner(f"Traitement — {slot['label']}…"):
                data = run_pipeline(sample_path.read_bytes(), sample_path.suffix)
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
                data = run_pipeline(uploaded.getvalue(), Path(uploaded.name).suffix)
            path, processed_image, raw_text, result = (
                data["path"],
                data["processed_image"],
                data["raw_text"],
                data["result"],
            )

    if result is not None:
        render_document_card(slot, path, processed_image, raw_text, result)
        filled_results.append({"slot": slot, "result": result, "raw_text": raw_text})
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

if identity_result["issues"]:
    # Priorité aux incohérences réellement détectées : la date de naissance
    # est comparée indépendamment du nom (verification/identity_checker.py)
    # et peut donc signaler une anomalie même quand moins de 2 documents
    # exposent un nom/prénom exploitable (comparable_documents < 2) - il ne
    # faut jamais masquer une incohérence détectée derrière ce message.
    st.error("🚫 Incohérence d'identité détectée entre plusieurs documents du dossier :")
    for issue in identity_result["issues"]:
        st.markdown(f"- {issue}")
    st.caption(
        "Le système signale l'anomalie mais ne rejette jamais automatiquement un "
        "dossier — la décision reste aux enseignants (rapport §1.5). La génération "
        "des questions d'entretien est toutefois bloquée tant que l'incohérence "
        "n'est pas résolue."
    )
elif identity_result["comparable_documents"] < 2:
    st.caption("Pas encore assez de documents avec un nom/prénom exploitable pour comparer.")
else:
    st.success(
        f"✅ Identité cohérente sur les {identity_result['comparable_documents']} "
        "documents comparés."
    )

# ---------- Cohérence des années universitaires (rapport §9) ----------
st.divider()
st.markdown("### Cohérence des années universitaires")

releve_fields = [item["result"]["fields"] for item in filled_results if item["result"]["document_type"] == "releve_notes"]
licence_fields = next(
    (item["result"]["fields"] for item in filled_results if item["result"]["document_type"] == "diplome_licence"), None
)
academic_years_result = check_academic_years(releve_fields, licence_fields)

if len(releve_fields) < 2:
    st.caption("Pas encore assez de relevés pour vérifier la cohérence des années.")
elif academic_years_result["consistent"]:
    st.success(f"✅ Années universitaires cohérentes sur les {len(releve_fields)} relevés fournis.")
else:
    st.error("🚫 Incohérence détectée dans les années universitaires :")
    for issue in academic_years_result["issues"]:
        st.markdown(f"- {issue}")

# ---------- Détection de documents dupliqués (rapport §9) ----------
st.divider()
st.markdown("### Documents dupliqués")

raw_text_documents = [{"label": item["slot"]["label"], "raw_text": item["raw_text"]} for item in filled_results]
duplicate_result = check_duplicate_documents(raw_text_documents)

if len(raw_text_documents) < 2:
    st.caption("Pas encore assez de documents pour détecter un doublon.")
elif duplicate_result["consistent"]:
    st.success("✅ Aucun document dupliqué détecté.")
else:
    st.error("🚫 Documents potentiellement dupliqués :")
    for issue in duplicate_result["issues"]:
        st.markdown(f"- {issue}")

# ---------- Aperçu du dossier ----------
st.divider()
st.markdown("### Aperçu du dossier")

nb_total = len(active_slots)
nb_fournis = len(filled_results)
nb_success = sum(1 for r in filled_results if r["result"]["extraction_status"] == "success")
nb_mismatch = sum(
    1 for r in filled_results
    if r["result"]["document_type"] != r["slot"]["key"] and r["result"]["document_type"] != "inconnu"
)

completeness = compute_completeness(
    active_slots, filled_results, identity_result, academic_years_result, duplicate_result
)
status_icon, status_label, status_css = COMPLETENESS_STATUS_LABELS[completeness["status"]]

col_score, col_status = st.columns([1, 3])
col_score.metric("Score de complétude", f"{completeness['score']:.0%}")
with col_status:
    st.markdown(f'Statut du dossier : <span class="{status_css}">{status_icon} {status_label}</span>', unsafe_allow_html=True)
    if completeness["missing_documents"]:
        st.caption("Documents manquants : " + ", ".join(completeness["missing_documents"]))

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Documents fournis", f"{nb_fournis} / {nb_total}")
col2.metric("Extractions complètes", f"{nb_success} / {nb_fournis}" if nb_fournis else "0 / 0")
col3.metric("Documents mal catégorisés", nb_mismatch)
col4.metric("Identité cohérente", "Oui" if identity_result["consistent"] else "Non")
col5.metric("Années cohérentes", "Oui" if academic_years_result["consistent"] else "Non")
col6.metric("Sans doublon", "Oui" if duplicate_result["consistent"] else "Non")

st.caption(
    "Score indicatif combinant présence des documents "
    f"({COMPLETENESS_WEIGHT_PRESENCE:.0%}), complétude de l'extraction "
    f"({COMPLETENESS_WEIGHT_EXTRACTION:.0%}) et cohérence "
    f"({COMPLETENESS_WEIGHT_COHERENCE:.0%}) - barème par défaut du POC, ajustable "
    "dans config/settings.py, en l'absence de barème officiel de l'encadrante "
    "(rapport §10). Ne remplace jamais la décision des enseignants (rapport §1.5) "
    "et ne couvre pas le niveau académique (moyennes minimales, mentions "
    "attendues), non défini à ce jour."
)

# ---------- Profil candidat : sauvegarde pour l'espace candidat ----------
documents_for_profile = [
    {"document_type": item["result"]["document_type"], "fields": item["result"]["fields"]}
    for item in filled_results
]
profile = build_candidate_profile(documents_for_profile) if filled_results else None
key = candidate_key(profile["nom_complet"]) if profile and profile.get("nom_complet") else None

if profile and key and identity_result["consistent"]:
    save_profile(key, profile)

# ---------- Résultat du quiz de pré-entretien (rempli côté candidat) ----------
st.divider()
st.markdown("### Quiz de pré-entretien du candidat")
st.caption(
    "Rempli par le candidat lui-même dans l'espace « Espace Candidat » (menu de "
    "gauche), à partir de son profil - visible ici une fois complété."
)

candidate_data = load_candidate_data(key) if key else None
if not key:
    st.caption("Dépose des documents avec un nom/prénom exploitable pour retrouver le quiz du candidat.")
elif not candidate_data or "score" not in candidate_data:
    st.caption(f"Aucun quiz complété pour « {profile['nom_complet']} » pour le moment.")
else:
    score, total = candidate_data["score"], candidate_data["total"]
    st.metric("Score au quiz de préparation", f"{score} / {total}")
    st.caption(f"Complété le {candidate_data.get('quiz_completed_at', '?')}")
    with st.expander("Détail des réponses du candidat"):
        for i, q in enumerate(candidate_data.get("quiz", [])):
            given = candidate_data.get("answers", [None] * len(candidate_data["quiz"]))[i]
            correct = q["correct_index"]
            icon = "✅" if given == correct else "❌"
            st.markdown(f"{icon} **{i + 1}. {q['question']}**")
            st.caption(
                f"Réponse du candidat : {q['options'][given] if given is not None else '(sans réponse)'} — "
                f"Bonne réponse : {q['options'][correct]}"
            )

# ---------- Questions d'entretien (Module 2, rapport §3.3) ----------
st.divider()
st.markdown("### Questions d'entretien (Module 2)")
st.caption(
    "Génère des questions adaptées au profil du candidat (spécialité, résultats, "
    "matières les mieux évaluées) à l'aide d'un LLM externe. Ce module n'intervient "
    "jamais dans la vérification documentaire ci-dessus (rapport §4.5)."
)

provider, api_key_input, model_input = llm_provider_selector(key_prefix="teacher")
nb_questions = st.number_input("Nombre de questions à générer", min_value=5, max_value=50, value=30, step=5)

can_generate = bool(filled_results) and identity_result["consistent"]
if not filled_results:
    st.caption("Dépose au moins un document du dossier pour générer des questions.")
elif not identity_result["consistent"]:
    st.caption("Génération bloquée : résous l'incohérence d'identité ci-dessus avant de continuer.")

if st.button("Générer les questions d'entretien", disabled=not can_generate):
    with st.expander("Profil candidat transmis au LLM"):
        st.json(profile)

    try:
        with st.spinner("Génération des questions en cours…"):
            questions = generate_interview_questions(
                profile, nb_questions=int(nb_questions), provider=provider, api_key=api_key_input, model=model_input
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
