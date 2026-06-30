"""LLM service for agent nodes."""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMService:
    """Centralized LLM access with retry logic."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            from app.services.llm_client import get_chat_llm

            self._llm = get_chat_llm(self.settings)
        return self._llm

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def invoke(self, system: str, user: str, retries: int = 3) -> str:
        """Invoke LLM with retry logic."""
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                response = await self.llm.ainvoke(
                    [SystemMessage(content=system), HumanMessage(content=user)]
                )
                content = response.content
                return content if isinstance(content, str) else str(content)
            except Exception as e:
                last_error = e
                logger.warning("LLM call attempt %d failed: %s", attempt + 1, e)
        raise RuntimeError(f"LLM call failed after {retries} retries: {last_error}")

    async def invoke_json(self, system: str, user: str, retries: int = 3) -> dict[str, Any]:
        """Invoke LLM and parse JSON response."""
        content = await self.invoke(system, user, retries)
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        raise ValueError(f"Could not parse JSON from LLM response: {content[:200]}")
