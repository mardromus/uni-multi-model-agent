"""Base tool interface and registry."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: ClassVar[str]
    description: ClassVar[str]

    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """Return JSON schema for tool input."""

    @abstractmethod
    def output_schema(self) -> dict[str, Any]:
        """Return JSON schema for tool output."""

    @abstractmethod
    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the tool and return structured output."""

    def info(self) -> dict[str, Any]:
        """Return tool metadata for API."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema(),
            "output_schema": self.output_schema(),
        }


class ToolRegistry:
    """Registry for discovering and executing tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    async def execute(self, name: str, **kwargs: Any) -> dict[str, Any]:
        tool = self.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        return await tool.run(**kwargs)


def get_tool_registry() -> ToolRegistry:
    """Factory for tool registry with all tools registered."""
    from app.tools.audio_tool import AudioTool
    from app.tools.code_analyzer_tool import CodeAnalyzerTool
    from app.tools.cross_input_reasoner_tool import CrossInputReasonerTool
    from app.tools.ocr_tool import OCRTool
    from app.tools.pdf_parser_tool import PDFParserTool
    from app.tools.sentiment_tool import SentimentTool
    from app.tools.summarizer_tool import SummarizerTool
    from app.tools.youtube_tool import YouTubeTool

    registry = ToolRegistry()
    for tool_cls in [
        OCRTool,
        PDFParserTool,
        AudioTool,
        YouTubeTool,
        SummarizerTool,
        SentimentTool,
        CodeAnalyzerTool,
        CrossInputReasonerTool,
    ]:
        registry.register(tool_cls())
    return registry
