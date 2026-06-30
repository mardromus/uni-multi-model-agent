"""Utility functions."""

import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

YOUTUBE_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})"
)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def extract_youtube_urls(text: str) -> list[str]:
    """Extract YouTube video URLs from text."""
    urls: list[str] = []
    for match in YOUTUBE_URL_PATTERN.finditer(text):
        video_id = match.group(1)
        urls.append(f"https://www.youtube.com/watch?v={video_id}")
    return list(dict.fromkeys(urls))


def extract_youtube_video_id(url: str) -> str | None:
    """Extract video ID from a YouTube URL."""
    match = YOUTUBE_URL_PATTERN.search(url)
    return match.group(1) if match else None


def detect_file_type(filename: str, content_type: str | None = None) -> str:
    """Detect file type from extension or content type."""
    ext = Path(filename).suffix.lower()
    type_map = {
        ".pdf": "pdf",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".gif": "image",
        ".webp": "image",
        ".bmp": "image",
        ".tiff": "image",
        ".mp3": "audio",
        ".wav": "audio",
        ".m4a": "audio",
        ".ogg": "audio",
        ".flac": "audio",
        ".webm": "audio",
    }
    if ext in type_map:
        return type_map[ext]
    if content_type:
        if "pdf" in content_type:
            return "pdf"
        if "image" in content_type:
            return "image"
        if "audio" in content_type:
            return "audio"
    return "unknown"


def estimate_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Estimate token count for text."""
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        # Fallback: ~4 chars per token
        return max(1, len(text) // 4)


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    input_price: float = 0.15,
    output_price: float = 0.60,
) -> float:
    """Estimate cost in USD (prices per 1M tokens)."""
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text for summaries."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
