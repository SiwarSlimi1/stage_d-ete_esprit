"""Espace candidat — quiz de pré-entretien (fonctionnalité demandée par
l'encadrante, en complément du Module 2 du rapport).

Le candidat s'identifie par son nom, récupère son profil académique (déjà
vérifié par un enseignant, ou construit ici à partir de ses diplômes/relevés),
puis passe un quiz à choix multiples généré par LLM à partir de ce profil pour
s'entraîner avant son véritable entretien. Le score est ensuite consultable
par l'enseignant dans l'espace de vérification (app.py).

Ce module ne décide jamais de l'admission du candidat : il ne sert qu'à
l'auto-préparation (même principe de non-substitution que le reste du système,
rapport §1.5).
"""
from pathlib import Path

import streamlit as st

from interview.question_generator import (
    LLMNotConfiguredError,
    build_candidate_profile,
    generate_interview_feedback,
    generate_interview_questions,
    generate_quiz_questions,
)
from interview.quiz_store import candidate_key, load as load_candidate_data, save_profile, save_quiz_result
from ui_common import find_sample, inject_esprit_theme, llm_provider_selector, render_document_card, run_pipeline

st.set_page_config(page_title="Espace Candidat — ESPRIT", page_icon="🎓", layout="wide")
inject_esprit_theme("Espace Candidat", "Quiz de pré-entretien — Admission parallèle 2025/2026")

st.info(
    "Ce quiz est un outil d'auto-entraînement : il t'aide à réviser avant ton "
    "entretien réel. Il ne remplace en aucun cas l'entretien, et n'influence pas "
    "la décision d'admission (rapport §1.5)."
)

PROFILE_SLOTS = [
    {"key": "bac", "label": "Diplôme du baccalauréat", "sample_prefix": "bac"},
    {"key": "diplome_licence", "label": "Diplôme de licence", "sample_prefix": "diplome_licence"},
    {"key": "releve_notes", "label": "Relevé de notes", "sample_prefix": "releve_notes"},
]

st.markdown("### 1. Identification")
nom_complet_input = st.text_input("Ton nom complet (tel qu'il apparaît sur tes documents)")

if not nom_complet_input.strip():
    st.caption("Saisis ton nom pour continuer.")
    st.stop()

key = candidate_key(nom_complet_input)
candidate_data = load_candidate_data(key) or {}
saved_profile = candidate_data.get("profile")

st.markdown("### 2. Ton profil académique")

if saved_profile:
    st.success("Profil retrouvé (déjà vérifié) — pas besoin de redéposer tes documents.")
    profile = saved_profile
    with st.expander("Voir mon profil"):
        st.json(profile)
else:
    st.caption(
        "Aucun profil enregistré pour ce nom. Dépose au moins ton diplôme de "
        "licence ou ton dernier relevé de notes pour construire ton profil."
    )
    use_samples = st.checkbox("Utiliser un document d'exemple (démo)", value=False)
    profile_documents = []

    for slot in PROFILE_SLOTS:
        path: Path | None = None
        result = None

        if use_samples:
            sample_path = find_sample(slot["sample_prefix"])
            if sample_path is not None:
                data = run_pipeline(sample_path.read_bytes(), sample_path.suffix)
                path = sample_path
                result = {**data["result"], "source_image": str(sample_path)}
        else:
            uploaded = st.file_uploader(
                f"Déposer : {slot['label']}", type=["png", "jpg", "jpeg"], key=f"cand_upload_{slot['key']}"
            )
            if uploaded is not None:
                with st.spinner(f"Traitement — {slot['label']}…"):
                    data = run_pipeline(uploaded.getvalue(), Path(uploaded.name).suffix)
                path, result = data["path"], data["result"]

        if result is not None:
            render_document_card(slot, path, data["processed_image"], data["raw_text"], result)
            profile_documents.append({"document_type": result["document_type"], "fields": result["fields"]})

    if profile_documents:
        profile = build_candidate_profile(profile_documents)
        profile["nom_complet"] = profile.get("nom_complet") or nom_complet_input
        save_profile(key, profile)
        st.success("Profil construit et enregistré.")
        with st.expander("Voir mon profil"):
            st.json(profile)
    else:
        profile = None

if not profile:
    st.caption("Dépose au moins un document ci-dessus pour générer ton quiz.")
    st.stop()

st.divider()
st.markdown("### 3. Génère ton quiz de pré-entretien")

provider, api_key_input, model_input = llm_provider_selector(key_prefix="candidate")
nb_questions = st.number_input("Nombre de questions", min_value=5, max_value=30, value=10, step=5)

if st.button("Générer mon quiz"):
    try:
        with st.spinner("Génération du quiz en cours…"):
            quiz = generate_quiz_questions(
                profile,
                nb_questions=int(nb_questions),
                provider=provider,
                api_key=api_key_input,
                model=model_input,
            )
        if not quiz:
            st.warning("Le LLM n'a renvoyé aucune question exploitable. Réessaie.")
        else:
            st.session_state["quiz"] = quiz
            st.session_state["quiz_submitted"] = False
    except LLMNotConfiguredError as exc:
        st.warning(str(exc))
    except ImportError:
        st.warning("Le paquet `openai` n'est pas installé. Lancez `pip install openai`.")
    except Exception as exc:  # noqa: BLE001 - affichage direct de l'erreur API pour le debug en démo
        st.error(f"Échec de l'appel au LLM : {exc}")

quiz = st.session_state.get("quiz")

if quiz:
    st.divider()
    st.markdown("### 4. Réponds au quiz")

    for i, question in enumerate(quiz):
        st.markdown('<div class="quiz-question">', unsafe_allow_html=True)
        st.radio(
            f"**{i + 1}. {question['question']}**",
            options=list(range(4)),
            format_func=lambda idx, q=question: q["options"][idx],
            index=None,
            key=f"quiz_answer_{i}",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Valider mes réponses"):
        answers = [st.session_state.get(f"quiz_answer_{i}") for i in range(len(quiz))]
        score = sum(1 for i, q in enumerate(quiz) if answers[i] == q["correct_index"])
        save_quiz_result(key, quiz, answers, score, len(quiz))
        st.session_state["quiz_submitted"] = True
        st.session_state["quiz_answers"] = answers
        st.session_state["quiz_score"] = score

    if st.session_state.get("quiz_submitted"):
        answers = st.session_state["quiz_answers"]
        score = st.session_state["quiz_score"]
        st.success(f"Résultat : {score} / {len(quiz)} — visible par l'enseignant dans son espace de vérification.")
        for i, q in enumerate(quiz):
            given = answers[i]
            correct = q["correct_index"]
            icon = "✅" if given == correct else "❌"
            st.markdown(f"{icon} **{i + 1}. {q['question']}**")
            st.caption(
                f"Ta réponse : {q['options'][given] if given is not None else '(sans réponse)'} — "
                f"Bonne réponse : {q['options'][correct]}"
            )

st.divider()
st.markdown("### 5. Entretien simulé (questions ouvertes)")
st.info(
    "Ce retour est un outil de préparation personnel : contrairement au score du quiz "
    "ci-dessus, il n'est **jamais transmis à l'enseignant ni lié à ton dossier** - et il "
    "ne constitue jamais un verdict d'admission ni une recommandation de spécialité "
    "(rapport §1.5)."
)

nb_mock_questions = st.number_input(
    "Nombre de questions", min_value=3, max_value=10, value=5, step=1, key="mock_nb_questions"
)

if st.button("Générer mes questions d'entretien simulé"):
    try:
        with st.spinner("Génération des questions en cours…"):
            mock_questions = generate_interview_questions(
                profile,
                nb_questions=int(nb_mock_questions),
                provider=provider,
                api_key=api_key_input,
                model=model_input,
            )
        if not mock_questions:
            st.warning("Le LLM n'a renvoyé aucune question exploitable. Réessaie.")
        else:
            st.session_state["mock_questions"] = mock_questions
            st.session_state["mock_feedback"] = None
    except LLMNotConfiguredError as exc:
        st.warning(str(exc))
    except ImportError:
        st.warning("Le paquet `openai` n'est pas installé. Lancez `pip install openai`.")
    except Exception as exc:  # noqa: BLE001 - affichage direct de l'erreur API pour le debug en démo
        st.error(f"Échec de l'appel au LLM : {exc}")

mock_questions = st.session_state.get("mock_questions")

if mock_questions:
    st.markdown("#### Réponds librement à chaque question, comme dans un vrai entretien")
    for i, question in enumerate(mock_questions):
        st.text_area(f"**{i + 1}. {question}**", key=f"mock_answer_{i}", height=100)

    if st.button("Obtenir mon retour de préparation"):
        qa_pairs = [
            {"question": q, "reponse": (st.session_state.get(f"mock_answer_{i}") or "").strip() or "(sans réponse)"}
            for i, q in enumerate(mock_questions)
        ]
        try:
            with st.spinner("Analyse de tes réponses en cours…"):
                feedback = generate_interview_feedback(
                    profile, qa_pairs, provider=provider, api_key=api_key_input, model=model_input
                )
            st.session_state["mock_feedback"] = feedback
        except LLMNotConfiguredError as exc:
            st.warning(str(exc))
        except ImportError:
            st.warning("Le paquet `openai` n'est pas installé. Lancez `pip install openai`.")
        except Exception as exc:  # noqa: BLE001 - affichage direct de l'erreur API pour le debug en démo
            st.error(f"Échec de l'appel au LLM : {exc}")

    feedback = st.session_state.get("mock_feedback")
    if feedback:
        st.markdown("#### Ton retour de préparation")
        for title, key in [
            ("Points forts", "points_forts"),
            ("Axes d'amélioration", "axes_amelioration"),
            ("Conseils pour l'entretien réel", "conseils_preparation"),
        ]:
            if feedback.get(key):
                st.markdown(f"**{title}**")
                for item in feedback[key]:
                    st.markdown(f"- {item}")
