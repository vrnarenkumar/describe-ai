"""
Shared LLM factory — returns a ChatModel based on the configured provider.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from .config import cfg


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Return a cached chat model instance (free providers only)."""
    if cfg.MODEL_PROVIDER == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=cfg.GROQ_MODEL,
            groq_api_key=cfg.GROQ_API_KEY,
            temperature=0.2,
        )
    elif cfg.MODEL_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=cfg.OLLAMA_MODEL,
            base_url=cfg.OLLAMA_BASE_URL,
            temperature=0.2,
        )
    else:
        raise ValueError(
            f"Unsupported MODEL_PROVIDER: '{cfg.MODEL_PROVIDER}'. "
            "Use 'groq' (free) or 'ollama' (local)."
        )
