"""Sentiment analysis tool."""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import get_settings
from app.services.llm_client import get_chat_llm
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SentimentTool(BaseTool):
    """Analyze sentiment of text content."""

    name = "sentiment"
    description = (
        "Analyze sentiment of text. Returns label (positive/negative/neutral/mixed), "
        "confidence score, and one-line justification."
    )

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to analyze"},
            },
            "required": ["text"],
        }

    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "label": {"type": "string", "enum": ["positive", "negative", "neutral", "mixed"]},
                "confidence": {"type": "number"},
                "justification": {"type": "string"},
                "error": {"type": "string", "nullable": True},
            },
        }

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        text = kwargs.get("text", "")

        if not text or len(text.strip()) < 5:
            return {
                "label": "neutral",
                "confidence": 0.0,
                "justification": "Insufficient text for sentiment analysis.",
                "error": "Text too short",
            }

        settings = get_settings()
        if not settings.cerebras_api_key:
            return self._rule_based_sentiment(text)

        try:
            llm = get_chat_llm(settings, temperature=0.1)

            prompt = f"""Analyze the sentiment of this text. Respond ONLY in valid JSON:
{{
  "label": "positive|negative|neutral|mixed",
  "confidence": 0.0-1.0,
  "justification": "one line explanation"
}}

Text:
{text[:4000]}"""

            response = await llm.ainvoke(
                [
                    SystemMessage(content="You are a sentiment analyzer. Output valid JSON only."),
                    HumanMessage(content=prompt),
                ]
            )

            content = response.content
            if isinstance(content, str):
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    parsed = json.loads(content[start:end])
                    return {
                        "label": parsed.get("label", "neutral"),
                        "confidence": float(parsed.get("confidence", 0.5)),
                        "justification": parsed.get("justification", ""),
                        "error": None,
                    }
        except Exception as e:
            logger.exception("Sentiment analysis failed")
            result = self._rule_based_sentiment(text)
            result["error"] = str(e)
            return result

        return self._rule_based_sentiment(text)

    @staticmethod
    def _rule_based_sentiment(text: str) -> dict[str, Any]:
        """Simple keyword-based fallback."""
        positive_words = {"good", "great", "excellent", "happy", "love", "amazing", "wonderful"}
        negative_words = {"bad", "terrible", "hate", "awful", "poor", "horrible", "sad", "angry"}
        words = set(text.lower().split())
        pos = len(words & positive_words)
        neg = len(words & negative_words)

        if pos > neg:
            label, conf = "positive", min(0.9, 0.5 + pos * 0.1)
        elif neg > pos:
            label, conf = "negative", min(0.9, 0.5 + neg * 0.1)
        else:
            label, conf = "neutral", 0.5

        return {
            "label": label,
            "confidence": conf,
            "justification": f"Rule-based analysis: {pos} positive and {neg} negative indicators.",
            "error": None,
        }
