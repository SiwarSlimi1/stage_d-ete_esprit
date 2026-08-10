"""Génération de questions d'entretien via LLM (Module 2, rapport §3.3, §4.5).

Ce module n'intervient jamais dans la vérification documentaire (Module 1) :
il exploite le profil du candidat une fois ses documents extraits, pour aider
les enseignants à préparer l'entretien de sélection - sans jamais se
substituer à leur jugement (rapport §1.5, §3.3).

Complète aussi, à la demande de l'encadrante, un quiz de pré-entretien (QCM)
que le candidat peut passer lui-même pour s'entraîner avant l'entretien réel
(generate_quiz_questions) - fonctionnalité hors périmètre initial du rapport.
"""
import json
import os

_SYSTEM_PROMPT = (
    "Tu es un enseignant d'ESPRIT qui prépare un entretien de sélection pour "
    "l'admission parallèle en 4ème année du cycle ingénieur. Tu génères des "
    "questions techniques et de motivation adaptées au profil académique du "
    "candidat. N'inclus jamais de question portant sur des critères personnels "
    "(origine, religion, situation familiale, apparence...) : uniquement des "
    "questions techniques liées à sa spécialité et à son parcours, et des "
    "questions de motivation/projet professionnel."
)

_QUIZ_SYSTEM_PROMPT = (
    "Tu es un enseignant d'ESPRIT qui prépare un quiz de pré-entretien pour "
    "aider un candidat à l'admission parallèle à s'entraîner avant son "
    "entretien de sélection. Le quiz porte sur des connaissances techniques "
    "liées à sa spécialité et à son parcours académique. N'inclus jamais de "
    "question portant sur des critères personnels (origine, religion, "
    "situation familiale, apparence...)."
)


class LLMNotConfiguredError(RuntimeError):
    """Levée quand aucune clé API LLM n'est disponible."""


def build_candidate_profile(documents: list[dict]) -> dict:
    """Construit le profil candidat structuré transmis au LLM, à partir des
    champs déjà extraits des documents du dossier (rapport §3.3) : spécialité
    de licence, résultats académiques généraux, matières les mieux évaluées.

    `documents` : liste de {"document_type": str, "fields": dict}.
    """
    profile = {
        "nom_complet": None,
        "specialite_licence": None,
        "annee_obtention_licence": None,
        "etablissement": None,
        "filiere_bac": None,
        "mention_bac": None,
        "releves": [],
        "matieres_les_mieux_evaluees": [],
    }

    all_matieres = []  # (note, matiere, annee)

    for doc in documents:
        fields = doc.get("fields", {})
        doc_type = doc.get("document_type")

        if not profile["nom_complet"]:
            if fields.get("nom") or fields.get("prenom"):
                profile["nom_complet"] = " ".join(v for v in (fields.get("nom"), fields.get("prenom")) if v)
            elif fields.get("etudiant"):
                profile["nom_complet"] = fields["etudiant"]

        if doc_type == "diplome_licence":
            profile["specialite_licence"] = fields.get("specialite")
            profile["annee_obtention_licence"] = fields.get("annee_obtention")
            profile["etablissement"] = fields.get("etablissement")

        elif doc_type == "bac":
            profile["filiere_bac"] = fields.get("filiere_bac")
            profile["mention_bac"] = fields.get("mention")

        elif doc_type == "releve_notes":
            annee = fields.get("annee_universitaire")
            matieres = fields.get("matieres") or []
            profile["releves"].append(
                {"annee": annee, "moyenne": fields.get("moyenne"), "nb_matieres": len(matieres)}
            )
            for matiere in matieres:
                note = matiere.get("note")
                if isinstance(note, (int, float)):
                    all_matieres.append((note, matiere.get("matiere"), annee))

    all_matieres.sort(key=lambda t: t[0], reverse=True)
    profile["matieres_les_mieux_evaluees"] = [
        {"matiere": matiere, "note": note, "annee": annee} for note, matiere, annee in all_matieres[:5]
    ]
    return profile


def _build_user_prompt(profile: dict, nb_questions: int) -> str:
    return (
        "Voici le profil du candidat, extrait automatiquement de son dossier de "
        f"candidature :\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n\n"
        f"Génère exactement {nb_questions} questions d'entretien, adaptées à sa "
        "spécialité et à son parcours académique (davantage de questions "
        "techniques sur les matières où il excelle, quelques questions de "
        "motivation et de projet professionnel). "
        f'Réponds uniquement avec un objet JSON de la forme {{"questions": '
        f'["...", ...]}} contenant exactement {nb_questions} questions, sans texte '
        "autour."
    )


# Fournisseurs LLM pris en charge : variable d'environnement attendue et modèle
# par défaut (gemini = fournisseur avec un palier gratuit, sans carte bancaire,
# recommandé pour tester ce module sans dépendre d'un compte OpenAI facturé).
_PROVIDER_ENV_VAR = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}
_PROVIDER_DEFAULT_MODEL = {"openai": "gpt-4o-mini", "gemini": "gemini-2.0-flash"}


def _call_openai(system_prompt: str, user_prompt: str, api_key: str, model: str) -> str:
    from openai import OpenAI  # import local : dépendance optionnelle du POC

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    return response.choices[0].message.content


def _call_gemini(system_prompt: str, user_prompt: str, api_key: str, model: str) -> str:
    """Appelle l'API REST Gemini (Google AI Studio) directement en HTTP, pour ne
    pas ajouter de dépendance SDK supplémentaire au projet."""
    import urllib.error
    import urllib.request

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = json.dumps(
        {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erreur API Gemini ({exc.code}) : {detail}") from exc
    return body["candidates"][0]["content"]["parts"][0]["text"]


def _resolve_provider_and_key(provider: str, api_key: str | None) -> tuple[str, str, str]:
    """Valide le fournisseur, résout la clé API (paramètre ou variable
    d'environnement) et le modèle par défaut. Lève LLMNotConfiguredError si
    aucune clé n'est disponible - jamais de repli silencieux."""
    provider = provider.lower()
    if provider not in _PROVIDER_ENV_VAR:
        raise ValueError(f"Fournisseur LLM inconnu : {provider!r} (attendu : openai, gemini)")

    env_var = _PROVIDER_ENV_VAR[provider]
    resolved_key = api_key or os.environ.get(env_var)
    if not resolved_key:
        raise LLMNotConfiguredError(
            f"Aucune clé API {provider} configurée. Définissez la variable "
            f"d'environnement {env_var} (ou transmettez une clé explicitement) pour "
            "activer ce module."
        )
    return provider, resolved_key, _PROVIDER_DEFAULT_MODEL[provider]


def _call_llm(provider: str, system_prompt: str, user_prompt: str, api_key: str, model: str) -> str:
    if provider == "openai":
        return _call_openai(system_prompt, user_prompt, api_key, model)
    return _call_gemini(system_prompt, user_prompt, api_key, model)


def generate_interview_questions(
    profile: dict,
    nb_questions: int = 30,
    provider: str = "gemini",
    api_key: str | None = None,
    model: str | None = None,
) -> list[str]:
    """Appelle le LLM pour générer des questions d'entretien adaptées au profil.

    `provider` : "gemini" (Google AI Studio, palier gratuit sans carte bancaire -
    recommandé par défaut) ou "openai".

    Lève LLMNotConfiguredError si aucune clé API n'est disponible (ni en
    paramètre, ni via la variable d'environnement correspondante) : le module
    ne doit jamais renvoyer de questions génériques inventées localement en
    remplacement d'un vrai appel au LLM, pour ne pas masquer une clé absente
    derrière un faux succès.
    """
    provider, api_key, default_model = _resolve_provider_and_key(provider, api_key)
    user_prompt = _build_user_prompt(profile, nb_questions)
    raw_text = _call_llm(provider, _SYSTEM_PROMPT, user_prompt, api_key, model or default_model)

    payload = json.loads(raw_text)
    questions = payload.get("questions", [])
    return questions[:nb_questions]


def _build_quiz_prompt(profile: dict, nb_questions: int) -> str:
    return (
        "Voici le profil du candidat, extrait automatiquement de son dossier de "
        f"candidature :\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n\n"
        f"Génère un quiz de pré-entretien de {nb_questions} questions à choix "
        "multiples (QCM), adapté à sa spécialité et à son parcours académique, "
        "pour l'aider à s'entraîner avant son entretien d'admission. Chaque "
        "question doit avoir exactement 4 options, une seule correcte. "
        f'Réponds uniquement avec un objet JSON de la forme {{"questions": '
        f'[{{"question": "...", "options": ["...", "...", "...", "..."], '
        f'"correct_index": 0}}, ...]}} contenant exactement {nb_questions} '
        "questions, sans texte autour. correct_index est l'indice (0 à 3) de la "
        "bonne réponse dans la liste options."
    )


def generate_quiz_questions(
    profile: dict,
    nb_questions: int = 10,
    provider: str = "gemini",
    api_key: str | None = None,
    model: str | None = None,
) -> list[dict]:
    """Génère un quiz de pré-entretien (QCM) adapté au profil du candidat, pour
    lui permettre de s'entraîner avant l'entretien réel - fonctionnalité
    demandée par l'encadrante en complément du Module 2 du rapport.

    Retourne une liste de {"question": str, "options": [4 str], "correct_index": int}.
    Les questions mal formées renvoyées par le LLM sont écartées plutôt que de
    faire planter l'interface.
    """
    provider, api_key, default_model = _resolve_provider_and_key(provider, api_key)
    user_prompt = _build_quiz_prompt(profile, nb_questions)
    raw_text = _call_llm(provider, _QUIZ_SYSTEM_PROMPT, user_prompt, api_key, model or default_model)

    payload = json.loads(raw_text)
    questions = payload.get("questions", [])
    valid = [
        q
        for q in questions
        if isinstance(q, dict)
        and q.get("question")
        and isinstance(q.get("options"), list)
        and len(q["options"]) == 4
        and isinstance(q.get("correct_index"), int)
        and 0 <= q["correct_index"] <= 3
    ]
    return valid[:nb_questions]
