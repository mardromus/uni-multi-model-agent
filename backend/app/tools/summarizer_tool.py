"""Summarizer tool using LLM for structured summaries."""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import get_settings
from app.services.llm_client import get_chat_llm
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SummarizerTool(BaseTool):
    """Generate structured summaries at three levels."""

    name = "summarizer"
    description = (
        "Summarize text content. Returns exactly: 1-line summary, "
        "3-bullet summary, and 5-sentence summary."
    )

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to summarize"},
                "context": {"type": "string", "description": "Optional context", "default": ""},
            },
            "required": ["text"],
        }

    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "one_line": {"type": "string"},
                "three_bullets": {"type": "array", "items": {"type": "string"}},
                "five_sentences": {"type": "string"},
                "error": {"type": "string", "nullable": True},
            },
        }

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        text = kwargs.get("text", "")
        context = kwargs.get("context", "")

        if not text or len(text.strip()) < 10:
            return {
                "one_line": "Insufficient text to summarize.",
                "three_bullets": ["No content provided."],
                "five_sentences": "No content was provided for summarization.",
                "error": "Text too short",
            }

        settings = get_settings()
        if not settings.openai_api_key:
            return self._fallback_summary(text)

        try:
            llm = get_chat_llm(settings, temperature=0.3)

            prompt = f"""Summarize the following text. Respond ONLY in valid JSON:
{{
  "one_line": "single sentence summary",
  "three_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "five_sentences": "A paragraph of exactly 5 sentences summarizing the content."
}}

Context: {context}
Text:
{text[:8000]}"""

            response = await llm.ainvoke(
                [
                    SystemMessage(content="You are a precise summarizer. Output valid JSON only."),
                    HumanMessage(content=prompt),
                ]
            )

            content = response.content
            if isinstance(content, str):
                # Extract JSON from response
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    parsed = json.loads(content[start:end])
                    return {
                        "one_line": parsed.get("one_line", ""),
                        "three_bullets": parsed.get("three_bullets", [])[:3],
                        "five_sentences": parsed.get("five_sentences", ""),
                        "error": None,
                    }
        except Exception as e:
            logger.exception("Summarizer LLM call failed")
            return {**self._fallback_summary(text), "error": str(e)}

        return self._fallback_summary(text)

    @staticmethod
    def _fallback_summary(text: str) -> dict[str, Any]:
        """Rule-based fallback when LLM unavailable."""
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        one_line = sentences[0][:200] + ("..." if len(sentences[0]) > 200 else "") if sentences else ""
        bullets = [s[:150] for s in sentences[:3]] or ["No summary available."]
        five = ". ".join(sentences[:5]) + "." if sentences else text[:500]
        return {
            "one_line": one_line,
            "three_bullets": bullets,
            "five_sentences": five,
            "error": None,
        }
