"""Seul endroit où l'on choisit le LLM. Le reste de l'agent ne connaît aucun fournisseur.

Chaîne : Groq (rapide) -> Groq (modèle de secours) -> Gemini (lent, indépendant).
Chaque bascule est signalée par un WARNING : jamais d'échec silencieux.
"""
import logging
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

log = logging.getLogger("safesite.llm")


def text_of(content) -> str:
    """Gemini renvoie parfois une liste de blocs ; on garde seulement le texte."""
    if isinstance(content, str):
        return content
    return "".join(
        b.get("text", "")
        for b in content
        if isinstance(b, dict) and b.get("type") == "text"
    )


class ChainedLLM:
    """Essaie chaque modèle dans l'ordre ; renvoie le texte de la 1re réponse réussie."""

    def __init__(self, models):
        self.models = models  # liste de (étiquette, modèle LangChain)

    def invoke(self, prompt) -> str:
        errors = []
        for i, (label, model) in enumerate(self.models):
            try:
                answer = text_of(model.invoke(prompt).content)
            except Exception as e:  # noqa: BLE001 - on veut tout capter ici
                errors.append(f"{label}: {type(e).__name__}")
                log.warning("LLM '%s' a échoué (%s: %s)", label, type(e).__name__, str(e)[:120])
                continue
            if i > 0:
                log.warning("REPLI ACTIF : réponse fournie par '%s' (échecs: %s)", label, errors)
            return answer
        raise RuntimeError(f"Tous les LLM ont échoué : {errors}")


def get_llm() -> ChainedLLM:
    groq_main = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    groq_alt = os.environ.get("GROQ_FALLBACK_MODEL", "qwen/qwen3.8-27b")
    gemini = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    return ChainedLLM([
        (f"groq/{groq_main}", ChatGroq(model=groq_main, temperature=0, timeout=20, max_retries=0)),
        (f"groq/{groq_alt}", ChatGroq(model=groq_alt, temperature=0, timeout=20, max_retries=0)),
        (f"gemini/{gemini}", ChatGoogleGenerativeAI(
            model=gemini, temperature=0, timeout=30, max_retries=0, thinking_level="minimal")),
    ])
