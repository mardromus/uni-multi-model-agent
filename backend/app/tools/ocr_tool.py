"""OCR tool using EasyOCR."""

import logging
from pathlib import Path
from typing import Any

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Lazy-loaded reader to avoid slow startup
_ocr_reader = None


def _get_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr

        _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _ocr_reader


class OCRTool(BaseTool):
    """Extract text from images using EasyOCR."""

    name = "ocr"
    description = (
        "Extract text from images using OCR. Returns extracted text, "
        "confidence scores, and bounding boxes for each detected text region."
    )

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to image file"},
                "languages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["en"],
                },
            },
            "required": ["file_path"],
        }

    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "confidence": {"type": "number"},
                "regions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "confidence": {"type": "number"},
                            "bbox": {
                                "type": "array",
                                "items": {"type": "array", "items": {"type": "number"}},
                            },
                        },
                    },
                },
                "error": {"type": "string", "nullable": True},
            },
        }

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        file_path = kwargs.get("file_path", "")
        if not file_path or not Path(file_path).exists():
            return {
                "text": "",
                "confidence": 0.0,
                "regions": [],
                "error": f"Image file not found: {file_path}",
            }

        try:
            reader = _get_reader()
            results = reader.readtext(file_path)

            regions = []
            all_text_parts: list[str] = []
            confidences: list[float] = []

            for bbox, text, conf in results:
                regions.append(
                    {
                        "text": text,
                        "confidence": float(conf),
                        "bbox": [[float(p[0]), float(p[1])] for p in bbox],
                    }
                )
                all_text_parts.append(text)
                confidences.append(float(conf))

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            extracted_text = "\n".join(all_text_parts)

            return {
                "text": extracted_text,
                "confidence": round(avg_confidence, 4),
                "regions": regions,
                "error": None,
            }
        except Exception as e:
            logger.exception("OCR failed for %s", file_path)
            return {
                "text": "",
                "confidence": 0.0,
                "regions": [],
                "error": f"OCR failed: {e!s}",
            }
