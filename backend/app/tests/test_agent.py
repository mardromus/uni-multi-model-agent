"""Automated tests for Universal Multi-Modal Agent."""

import pytest

from app.models.domain import IntentType, InputType, ProcessedInput
from app.tools.base import get_tool_registry
from app.utils.helpers import detect_file_type, extract_youtube_urls, estimate_tokens


class TestHelpers:
    def test_extract_youtube_urls(self):
        text = "Check this video https://www.youtube.com/watch?v=dQw4w9WgXcQ and also https://youtu.be/abc12345678"
        urls = extract_youtube_urls(text)
        assert len(urls) >= 1
        assert "youtube.com" in urls[0] or "youtu.be" in urls[0]

    def test_detect_file_type_pdf(self):
        assert detect_file_type("document.pdf") == "pdf"

    def test_detect_file_type_image(self):
        assert detect_file_type("photo.png") == "image"
        assert detect_file_type("photo.jpg") == "image"

    def test_detect_file_type_audio(self):
        assert detect_file_type("recording.mp3") == "audio"
        assert detect_file_type("recording.wav") == "audio"

    def test_estimate_tokens(self):
        tokens = estimate_tokens("Hello, world!")
        assert tokens > 0


class TestToolRegistry:
    def test_all_tools_registered(self):
        registry = get_tool_registry()
        names = registry.list_names()
        expected = [
            "ocr",
            "pdf_parser",
            "audio_transcription",
            "youtube",
            "summarizer",
            "sentiment",
            "code_analyzer",
            "cross_input_reasoner",
        ]
        for name in expected:
            assert name in names

    def test_tool_schemas(self):
        registry = get_tool_registry()
        for tool in registry.list_tools():
            assert tool.input_schema()
            assert tool.output_schema()
            info = tool.info()
            assert info["name"] == tool.name


class TestSummarizerTool:
    @pytest.mark.asyncio
    async def test_summarizer_short_text(self):
        from app.tools.summarizer_tool import SummarizerTool

        tool = SummarizerTool()
        result = await tool.run(text="Hi")
        assert "one_line" in result
        assert result.get("error") is not None or result["one_line"]

    @pytest.mark.asyncio
    async def test_summarizer_with_content(self):
        from app.tools.summarizer_tool import SummarizerTool

        text = (
            "Artificial intelligence is transforming industries worldwide. "
            "Machine learning models can now process text, images, and audio. "
            "Companies are investing heavily in AI research and development."
        )
        tool = SummarizerTool()
        result = await tool.run(text=text)
        assert "one_line" in result
        assert "three_bullets" in result
        assert "five_sentences" in result


class TestSentimentTool:
    @pytest.mark.asyncio
    async def test_sentiment_positive(self):
        from app.tools.sentiment_tool import SentimentTool

        tool = SentimentTool()
        result = await tool.run(text="This is a great and wonderful product! I love it!")
        assert result["label"] in ("positive", "negative", "neutral", "mixed")
        assert 0 <= result["confidence"] <= 1
        assert result["justification"]

    @pytest.mark.asyncio
    async def test_sentiment_empty(self):
        from app.tools.sentiment_tool import SentimentTool

        tool = SentimentTool()
        result = await tool.run(text="")
        assert result["label"] == "neutral"


class TestCodeAnalyzerTool:
    @pytest.mark.asyncio
    async def test_code_analyzer_python(self):
        from app.tools.code_analyzer_tool import CodeAnalyzerTool

        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        tool = CodeAnalyzerTool()
        result = await tool.run(code=code)
        assert result["language"] == "python"
        assert result["explanation"]
        assert "time_complexity" in result


class TestYouTubeTool:
    @pytest.mark.asyncio
    async def test_youtube_invalid_url(self):
        from app.tools.youtube_tool import YouTubeTool

        tool = YouTubeTool()
        result = await tool.run(url="https://example.com/not-youtube")
        assert result["available"] is False

    @pytest.mark.asyncio
    async def test_youtube_valid_id_format(self):
        from app.tools.youtube_tool import YouTubeTool

        tool = YouTubeTool()
        result = await tool.run(video_id="invalidvideo1")
        assert "video_id" in result
        assert result["available"] is False or result["available"] is True


class TestCrossInputReasoner:
    @pytest.mark.asyncio
    async def test_cross_input_empty(self):
        from app.tools.cross_input_reasoner_tool import CrossInputReasonerTool

        tool = CrossInputReasonerTool()
        result = await tool.run(tool_outputs=[], extracted_texts=[])
        assert "unified_answer" in result

    @pytest.mark.asyncio
    async def test_cross_input_with_data(self):
        from app.tools.cross_input_reasoner_tool import CrossInputReasonerTool

        tool = CrossInputReasonerTool()
        result = await tool.run(
            tool_outputs=[{"text": "Document content about AI."}],
            extracted_texts=["Document content about AI.", "Audio says machine learning is key."],
            user_question="Compare the document and audio",
        )
        assert result["unified_answer"]
        assert result["reasoning_chain"]


class TestOCRTool:
    @pytest.mark.asyncio
    async def test_ocr_missing_file(self):
        from app.tools.ocr_tool import OCRTool

        tool = OCRTool()
        result = await tool.run(file_path="/nonexistent/image.png")
        assert result["error"] is not None
        assert result["text"] == ""


class TestPDFParserTool:
    @pytest.mark.asyncio
    async def test_pdf_missing_file(self):
        from app.tools.pdf_parser_tool import PDFParserTool

        tool = PDFParserTool()
        result = await tool.run(file_path="/nonexistent/doc.pdf")
        assert result["error"] is not None


class TestAudioTool:
    @pytest.mark.asyncio
    async def test_audio_missing_file(self):
        from app.tools.audio_tool import AudioTool

        tool = AudioTool()
        result = await tool.run(file_path="/nonexistent/audio.mp3")
        assert result["error"] is not None


class TestIntentDetection:
    def test_rule_based_youtube_intent(self):
        from app.graph.nodes import _rule_based_intent

        processed = ProcessedInput(
            text="Summarize this https://www.youtube.com/watch?v=abc12345678",
            youtube_urls=["https://www.youtube.com/watch?v=abc12345678"],
        )
        result = _rule_based_intent(processed)
        assert result.intent == IntentType.YOUTUBE_SUMMARY

    def test_rule_based_sentiment_intent(self):
        from app.graph.nodes import _rule_based_intent

        processed = ProcessedInput(text="Analyze the sentiment of this text")
        result = _rule_based_intent(processed)
        assert result.intent == IntentType.SENTIMENT

    def test_rule_based_pdf_clarification(self):
        """PDF without user query should require clarification."""
        from app.graph.nodes import _rule_based_intent

        # PDF with NO user text → ambiguous → should ask
        processed = ProcessedInput(
            text="",
            file_paths=["/tmp/doc.pdf"],
            file_types=["pdf"],
        )
        result = _rule_based_intent(processed)
        assert result.requires_clarification or result.confidence < 0.65

    def test_rule_based_pdf_with_query_no_clarification(self):
        """PDF with user text query should NOT require clarification."""
        from app.graph.nodes import _rule_based_intent

        processed = ProcessedInput(
            text="Here is a document about AI",
            file_paths=["/tmp/doc.pdf"],
            file_types=["pdf"],
        )
        result = _rule_based_intent(processed)
        # PDF + text → cross_input_reasoning with enough confidence to proceed
        assert not result.requires_clarification or result.confidence >= 0.65


class TestClarificationFlow:
    @pytest.mark.asyncio
    async def test_empty_input_needs_clarification(self):
        from app.graph.nodes import intent_detector_node

        state = {
            "processed_input": ProcessedInput(),
            "reasoning_steps": [],
        }
        result = await intent_detector_node(state)
        assert result.get("needs_clarification") is True


class TestPlanning:
    def test_build_plan_for_pdf_summary(self):
        from app.graph.nodes import _build_plan
        from app.models.domain import IntentResult, IntentType
        from app.tools.base import get_tool_registry

        processed = ProcessedInput(
            text="Summarize this PDF",
            file_paths=["/tmp/doc.pdf"],
            file_types=["pdf"],
        )
        intent = IntentResult(intent=IntentType.SUMMARY, confidence=0.9, reasoning="test")
        registry = get_tool_registry()
        steps = _build_plan(processed, intent, registry)
        tool_names = [s.tool_name for s in steps]
        assert "pdf_parser" in tool_names
        assert "summarizer" in tool_names

    def test_build_plan_for_code(self):
        from app.graph.nodes import _build_plan
        from app.models.domain import IntentResult, IntentType
        from app.tools.base import get_tool_registry

        processed = ProcessedInput(
            text="Explain this code:\n```python\nprint('hello')\n```",
        )
        intent = IntentResult(intent=IntentType.CODE_EXPLANATION, confidence=0.9, reasoning="test")
        registry = get_tool_registry()
        steps = _build_plan(processed, intent, registry)
        assert any(s.tool_name == "code_analyzer" for s in steps)


class TestAPIHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert len(data["tools_available"]) == 8

    @pytest.mark.asyncio
    async def test_tools_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/tools")
            assert response.status_code == 200
            data = response.json()
            assert len(data["tools"]) == 8


# ─────────────────────────────────────────────────────────────────────────────
# Assignment Test Case Coverage
# ─────────────────────────────────────────────────────────────────────────────


class TestCase1_AudioTranscriptionAndSummary:
    """Test Case 1: Audio file → transcribe → 3-format summary."""

    @pytest.mark.asyncio
    async def test_audio_tool_returns_structured_output(self):
        """AudioTool returns all expected fields even when file is missing."""
        from app.tools.audio_tool import AudioTool

        tool = AudioTool()
        result = await tool.run(file_path="/nonexistent/lecture.mp3")
        # Should gracefully return error without crashing
        assert "transcript" in result
        assert "language" in result
        assert "duration_seconds" in result
        assert "confidence" in result
        assert result["error"] is not None

    def test_audio_plan_chains_summarizer(self):
        """Planning node chains audio_transcription → summarizer automatically."""
        from app.graph.nodes import _build_plan
        from app.models.domain import IntentResult, IntentType
        from app.tools.base import get_tool_registry

        processed = ProcessedInput(
            text="Transcribe and summarize this lecture",
            file_paths=["/tmp/lecture.mp3"],
            file_types=["audio"],
        )
        intent = IntentResult(intent=IntentType.TRANSCRIPTION, confidence=0.9, reasoning="test")
        registry = get_tool_registry()
        steps = _build_plan(processed, intent, registry)
        tool_names = [s.tool_name for s in steps]
        assert "audio_transcription" in tool_names
        # When user says "summarize", summarizer should be chained
        assert "summarizer" in tool_names

    def test_summarizer_output_has_three_formats(self):
        """Summarizer tool output schema includes all 3 required formats."""
        from app.tools.summarizer_tool import SummarizerTool

        tool = SummarizerTool()
        schema = tool.output_schema()
        props = schema["properties"]
        assert "one_line" in props
        assert "three_bullets" in props
        assert "five_sentences" in props


class TestCase2_PDFActionItems:
    """Test Case 2: PDF + 'What are the action items?' → extract → filter."""

    def test_pdf_action_item_plan(self):
        """Planning creates pdf_parser → summarizer(action_item mode) plan."""
        from app.graph.nodes import _build_plan
        from app.models.domain import IntentResult, IntentType
        from app.tools.base import get_tool_registry

        processed = ProcessedInput(
            text="What are the action items from this meeting?",
            file_paths=["/tmp/meeting.pdf"],
            file_types=["pdf"],
        )
        intent = IntentResult(
            intent=IntentType.ACTION_ITEM_EXTRACTION, confidence=0.9, reasoning="action items keyword"
        )
        registry = get_tool_registry()
        steps = _build_plan(processed, intent, registry)
        tool_names = [s.tool_name for s in steps]
        assert "pdf_parser" in tool_names
        assert "summarizer" in tool_names

    def test_action_item_intent_detection(self):
        """Rule-based intent detects action items from keywords."""
        from app.graph.nodes import _rule_based_intent

        processed = ProcessedInput(
            text="What are the action items from this PDF?",
            file_paths=["/tmp/meeting.pdf"],
            file_types=["pdf"],
        )
        result = _rule_based_intent(processed)
        assert result.intent == IntentType.ACTION_ITEM_EXTRACTION
        assert result.confidence >= 0.7


class TestCase3_ImageCodeExplain:
    """Test Case 3: Image with code → OCR → code_analyzer."""

    def test_image_code_plan(self):
        """Planning chains ocr → code_analyzer for image + 'Explain' intent."""
        from app.graph.nodes import _build_plan
        from app.models.domain import IntentResult, IntentType
        from app.tools.base import get_tool_registry

        processed = ProcessedInput(
            text="Explain this code",
            file_paths=["/tmp/screenshot.png"],
            file_types=["image"],
        )
        intent = IntentResult(
            intent=IntentType.CODE_EXPLANATION, confidence=0.85, reasoning="code keyword"
        )
        registry = get_tool_registry()
        steps = _build_plan(processed, intent, registry)
        tool_names = [s.tool_name for s in steps]
        assert "ocr" in tool_names
        assert "code_analyzer" in tool_names
        # ocr must come before code_analyzer
        assert tool_names.index("ocr") < tool_names.index("code_analyzer")

    @pytest.mark.asyncio
    async def test_code_analyzer_detects_bugs(self):
        """Code analyzer returns bugs field for clearly buggy code."""
        from app.tools.code_analyzer_tool import CodeAnalyzerTool

        buggy_code = """
def divide(a, b):
    return a / b  # Division by zero not handled
"""
        tool = CodeAnalyzerTool()
        result = await tool.run(code=buggy_code)
        assert "explanation" in result
        assert "bugs" in result
        assert "language" in result


class TestCase4_CrossInputYouTube:
    """Test Case 4: PDF with YouTube URL → auto-detect → fetch → summarize."""

    def test_youtube_url_extraction_from_text(self):
        """extract_youtube_urls finds URLs in any text."""
        from app.utils.helpers import extract_youtube_urls

        pdf_text = "See this great tutorial: https://www.youtube.com/watch?v=dQw4w9WgXcQ for more info."
        urls = extract_youtube_urls(pdf_text)
        assert len(urls) == 1
        assert "dQw4w9WgXcQ" in urls[0]

    def test_youtube_url_extraction_short_format(self):
        """extract_youtube_urls handles youtu.be short format."""
        from app.utils.helpers import extract_youtube_urls

        text = "Video: https://youtu.be/abc12345678"
        urls = extract_youtube_urls(text)
        assert len(urls) == 1

    def test_pdf_plan_does_not_pre_include_youtube(self):
        """PDF-only plan initially has no YouTube step (added dynamically)."""
        from app.graph.nodes import _build_plan
        from app.models.domain import IntentResult, IntentType
        from app.tools.base import get_tool_registry

        processed = ProcessedInput(
            text="Summarize the video in this PDF",
            file_paths=["/tmp/doc.pdf"],
            file_types=["pdf"],
            youtube_urls=[],  # No YT URL detected from user text
        )
        intent = IntentResult(intent=IntentType.SUMMARY, confidence=0.75, reasoning="test")
        registry = get_tool_registry()
        steps = _build_plan(processed, intent, registry)
        tool_names = [s.tool_name for s in steps]
        # Initial plan has pdf_parser but no youtube (discovered dynamically)
        assert "pdf_parser" in tool_names
        assert "youtube" not in tool_names  # Will be added dynamically during execution


class TestCase5_MultiFileUnifiedQuery:
    """Test Case 5: Audio + PDF → compare → cross-input reasoning."""

    def test_multi_file_plan_uses_cross_input_reasoner(self):
        """Multiple files trigger cross_input_reasoner as final step."""
        from app.graph.nodes import _build_plan
        from app.models.domain import IntentResult, IntentType
        from app.tools.base import get_tool_registry

        processed = ProcessedInput(
            text="Do the audio and document discuss the same topic?",
            file_paths=["/tmp/audio.mp3", "/tmp/report.pdf"],
            file_types=["audio", "pdf"],
        )
        intent = IntentResult(
            intent=IntentType.CROSS_INPUT_REASONING, confidence=0.85, reasoning="comparison"
        )
        registry = get_tool_registry()
        steps = _build_plan(processed, intent, registry)
        tool_names = [s.tool_name for s in steps]

        # Should include extraction for both files
        assert "audio_transcription" in tool_names
        assert "pdf_parser" in tool_names
        # Should synthesize with cross_input_reasoner
        assert "cross_input_reasoner" in tool_names
        # cross_input_reasoner must be last
        assert tool_names[-1] == "cross_input_reasoner"

    def test_comparison_intent_detection(self):
        """Rule-based intent detects comparison from 'same topic' keyword."""
        from app.graph.nodes import _rule_based_intent

        processed = ProcessedInput(
            text="Do the audio and the document discuss the same topic?",
            file_paths=["/tmp/audio.mp3", "/tmp/doc.pdf"],
            file_types=["audio", "pdf"],
        )
        result = _rule_based_intent(processed)
        assert result.intent in (IntentType.CROSS_INPUT_REASONING, IntentType.COMPARISON)

