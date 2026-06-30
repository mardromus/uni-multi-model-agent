"""Code analyzer tool."""

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import get_settings
from app.services.llm_client import get_chat_llm
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

LANGUAGE_PATTERNS: dict[str, list[str]] = {
    "python": [r"\bdef\b", r"\bimport\b", r"\bclass\b", r":\s*$", r"print\("],
    "javascript": [r"\bfunction\b", r"\bconst\b", r"\blet\b", r"=>", r"console\.log"],
    "typescript": [r"\binterface\b", r":\s*string", r":\s*number", r"\btype\b"],
    "java": [r"\bpublic class\b", r"\bvoid\b", r"\bSystem\.out"],
    "csharp": [r"\bnamespace\b", r"\busing System", r"\bpublic class\b"],
    "go": [r"\bpackage\b", r"\bfunc\b", r":="],
    "rust": [r"\bfn\b", r"\blet mut\b", r"\bimpl\b"],
    "cpp": [r"#include", r"\bstd::", r"\bcout\b"],
    "sql": [r"\bSELECT\b", r"\bFROM\b", r"\bINSERT\b", r"\bCREATE TABLE\b"],
}


class CodeAnalyzerTool(BaseTool):
    """Analyze code: detect language, explain, find bugs, suggest improvements."""

    name = "code_analyzer"
    description = (
        "Analyze programming code. Detects language, explains code, finds bugs, "
        "suggests improvements, and estimates time/space complexity."
    )

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code to analyze"},
                "language_hint": {"type": "string", "nullable": True},
            },
            "required": ["code"],
        }

    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {"type": "string"},
                "explanation": {"type": "string"},
                "bugs": {"type": "array", "items": {"type": "string"}},
                "improvements": {"type": "array", "items": {"type": "string"}},
                "time_complexity": {"type": "string"},
                "space_complexity": {"type": "string"},
                "error": {"type": "string", "nullable": True},
            },
        }

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        code = kwargs.get("code", "")
        language_hint = kwargs.get("language_hint")

        if not code or len(code.strip()) < 5:
            return {
                "language": "unknown",
                "explanation": "No code provided.",
                "bugs": [],
                "improvements": [],
                "time_complexity": "N/A",
                "space_complexity": "N/A",
                "error": "Code too short",
            }

        detected_lang = language_hint or self._detect_language(code)
        settings = get_settings()

        if not settings.cerebras_api_key:
            return self._basic_analysis(code, detected_lang)

        try:
            llm = get_chat_llm(settings, temperature=0.2)

            prompt = f"""Analyze this {detected_lang} code. Respond ONLY in valid JSON:
{{
  "language": "detected language",
  "explanation": "clear explanation of what the code does",
  "bugs": ["potential bug 1", "potential bug 2"],
  "improvements": ["improvement 1", "improvement 2"],
  "time_complexity": "O(...) with explanation",
  "space_complexity": "O(...) with explanation"
}}

Code:
```
{code[:6000]}
```"""

            response = await llm.ainvoke(
                [
                    SystemMessage(content="You are an expert code reviewer. Output valid JSON only."),
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
                        "language": parsed.get("language", detected_lang),
                        "explanation": parsed.get("explanation", ""),
                        "bugs": parsed.get("bugs", []),
                        "improvements": parsed.get("improvements", []),
                        "time_complexity": parsed.get("time_complexity", "Unknown"),
                        "space_complexity": parsed.get("space_complexity", "Unknown"),
                        "error": None,
                    }
        except Exception as e:
            logger.exception("Code analysis failed")
            result = self._basic_analysis(code, detected_lang)
            result["error"] = str(e)
            return result

        return self._basic_analysis(code, detected_lang)

    @staticmethod
    def _detect_language(code: str) -> str:
        scores: dict[str, int] = {}
        for lang, patterns in LANGUAGE_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, code, re.MULTILINE))
            if score > 0:
                scores[lang] = score
        return max(scores, key=scores.get) if scores else "unknown"

    @staticmethod
    def _basic_analysis(code: str, language: str) -> dict[str, Any]:
        lines = code.strip().split("\n")
        return {
            "language": language,
            "explanation": f"This appears to be {language} code with {len(lines)} lines.",
            "bugs": [],
            "improvements": ["Add type hints", "Add error handling", "Add unit tests"],
            "time_complexity": "Unable to determine without LLM",
            "space_complexity": "Unable to determine without LLM",
            "error": None,
        }
