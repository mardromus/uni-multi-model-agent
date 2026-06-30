"""Cross-input reasoner tool for combining multiple tool outputs."""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import get_settings
from app.services.llm_client import get_chat_llm
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class CrossInputReasonerTool(BaseTool):
    """Combine outputs from multiple tools into a unified answer."""

    name = "cross_input_reasoner"
    description = (
        "Accept outputs from multiple tools and produce a unified, coherent answer "
        "by combining all extracted information."
    )

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tool_outputs": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of tool output dicts",
                },
                "user_question": {"type": "string", "description": "Original user question"},
                "extracted_texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "All extracted text segments",
                },
            },
            "required": ["tool_outputs"],
        }

    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "unified_answer": {"type": "string"},
                "key_insights": {"type": "array", "items": {"type": "string"}},
                "sources_used": {"type": "array", "items": {"type": "string"}},
                "reasoning_chain": {"type": "array", "items": {"type": "string"}},
                "error": {"type": "string", "nullable": True},
            },
        }

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        tool_outputs = kwargs.get("tool_outputs", [])
        user_question = kwargs.get("user_question", "")
        extracted_texts = kwargs.get("extracted_texts", [])

        if not tool_outputs and not extracted_texts:
            return {
                "unified_answer": "No inputs available for cross-input reasoning.",
                "key_insights": [],
                "sources_used": [],
                "reasoning_chain": ["No data to process"],
                "error": "Empty inputs",
            }

        settings = get_settings()
        combined_context = self._build_context(tool_outputs, extracted_texts)

        if not settings.openai_api_key:
            return self._fallback_reasoning(combined_context, user_question)

        try:
            llm = get_chat_llm(settings, temperature=0.4)

            prompt = f"""Combine the following multi-source information into a unified answer.

User question: {user_question}

Combined tool outputs and extracted texts:
{combined_context[:10000]}

Respond ONLY in valid JSON:
{{
  "unified_answer": "comprehensive unified answer",
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "sources_used": ["source description 1", "source description 2"],
  "reasoning_chain": ["step 1", "step 2", "step 3"]
}}"""

            response = await llm.ainvoke(
                [
                    SystemMessage(
                        content="You synthesize multi-modal inputs into coherent answers. JSON only."
                    ),
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
                        "unified_answer": parsed.get("unified_answer", ""),
                        "key_insights": parsed.get("key_insights", []),
                        "sources_used": parsed.get("sources_used", []),
                        "reasoning_chain": parsed.get("reasoning_chain", []),
                        "error": None,
                    }
        except Exception as e:
            logger.exception("Cross-input reasoning failed")
            result = self._fallback_reasoning(combined_context, user_question)
            result["error"] = str(e)
            return result

        return self._fallback_reasoning(combined_context, user_question)

    @staticmethod
    def _build_context(tool_outputs: list[dict], extracted_texts: list[str]) -> str:
        parts = []
        for i, output in enumerate(tool_outputs):
            parts.append(f"--- Tool Output {i + 1} ---\n{json.dumps(output, indent=2, default=str)}")
        for i, text in enumerate(extracted_texts):
            parts.append(f"--- Extracted Text {i + 1} ---\n{text[:2000]}")
        return "\n\n".join(parts)

    @staticmethod
    def _fallback_reasoning(context: str, question: str) -> dict[str, Any]:
        preview = context[:500] + "..." if len(context) > 500 else context
        return {
            "unified_answer": f"Based on the combined inputs: {preview}",
            "key_insights": ["Multiple sources were processed"],
            "sources_used": ["Combined tool outputs"],
            "reasoning_chain": [
                "Collected all tool outputs",
                "Merged extracted texts",
                f"Attempted to answer: {question or 'general query'}",
            ],
            "error": None,
        }
