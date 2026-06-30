"""Audio transcription tool using Whisper."""

import logging
from pathlib import Path
from typing import Any

from app.config.settings import get_settings
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper

        settings = get_settings()
        _whisper_model = whisper.load_model(settings.whisper_model)
    return _whisper_model


class AudioTool(BaseTool):
    """Transcribe audio files using OpenAI Whisper."""

    name = "audio_transcription"
    description = (
        "Transcribe audio files to text using Whisper. "
        "Returns transcript, detected language, duration, and confidence."
    )

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to audio file"},
                "language": {
                    "type": "string",
                    "description": "Optional language hint (ISO 639-1)",
                    "nullable": True,
                },
            },
            "required": ["file_path"],
        }

    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "transcript": {"type": "string"},
                "language": {"type": "string"},
                "duration_seconds": {"type": "number"},
                "confidence": {"type": "number"},
                "segments": {"type": "array"},
                "error": {"type": "string", "nullable": True},
            },
        }

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        file_path = kwargs.get("file_path", "")
        language_hint = kwargs.get("language")

        if not file_path or not Path(file_path).exists():
            return {
                "transcript": "",
                "language": "unknown",
                "duration_seconds": 0.0,
                "confidence": 0.0,
                "segments": [],
                "error": f"Audio file not found: {file_path}",
            }

        try:
            model = _get_whisper_model()
            options: dict[str, Any] = {"fp16": False}
            if language_hint:
                options["language"] = language_hint

            result = model.transcribe(file_path, **options)

            segments = []
            confidences: list[float] = []
            for seg in result.get("segments", []):
                seg_data = {
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": seg.get("text", ""),
                }
                if "avg_logprob" in seg:
                    conf = min(1.0, max(0.0, 1.0 + seg["avg_logprob"]))
                    seg_data["confidence"] = conf
                    confidences.append(conf)
                segments.append(seg_data)

            duration = segments[-1]["end"] if segments else 0.0
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.85

            return {
                "transcript": result.get("text", "").strip(),
                "language": result.get("language", "unknown"),
                "duration_seconds": round(duration, 2),
                "confidence": round(avg_confidence, 4),
                "segments": segments,
                "error": None,
            }
        except Exception as e:
            logger.exception("Audio transcription failed for %s", file_path)
            return {
                "transcript": "",
                "language": "unknown",
                "duration_seconds": 0.0,
                "confidence": 0.0,
                "segments": [],
                "error": f"Transcription failed: {e!s}",
            }
