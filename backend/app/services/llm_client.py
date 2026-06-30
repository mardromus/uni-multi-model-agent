"""Lazy LLM client to avoid heavy imports at module load."""

from typing import TYPE_CHECKING

from app.config.settings import Settings, get_settings

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI


def get_chat_llm(settings: Settings | None = None, temperature: float = 0.3) -> "ChatOpenAI":
    """Create ChatOpenAI instance with lazy import."""
    from langchain_openai import ChatOpenAI

    cfg = settings or get_settings()
    return ChatOpenAI(
        model=cfg.model_name,
        api_key=cfg.openai_api_key or "not-set",
        base_url=cfg.openai_base_url,
        temperature=temperature,
    )
