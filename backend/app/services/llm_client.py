"""Lazy LLM client to avoid heavy imports at module load."""

from typing import TYPE_CHECKING

from app.config.settings import Settings, get_settings

if TYPE_CHECKING:
    from langchain_cerebras import ChatCerebras


def get_chat_llm(settings: Settings | None = None, temperature: float = 0.3) -> "ChatCerebras":
    """Create ChatCerebras instance with lazy import."""
    from langchain_cerebras import ChatCerebras

    cfg = settings or get_settings()
    return ChatCerebras(
        model=cfg.model_name,
        api_key=cfg.cerebras_api_key or "not-set",
        base_url=cfg.cerebras_base_url,
        temperature=temperature,
    )
