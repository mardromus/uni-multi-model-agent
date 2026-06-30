"""YouTube transcript extraction tool."""

import logging
from typing import Any

from app.tools.base import BaseTool
from app.utils.helpers import extract_youtube_video_id

logger = logging.getLogger(__name__)


class YouTubeTool(BaseTool):
    """Fetch YouTube video transcripts using youtube-transcript-api."""

    name = "youtube"
    description = (
        "Detect and fetch YouTube video transcripts. "
        "Returns transcript text or graceful fallback if unavailable."
    )

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "YouTube video URL"},
                "video_id": {"type": "string", "description": "YouTube video ID (alternative to url)"},
            },
        }

    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "transcript": {"type": "string"},
                "video_id": {"type": "string"},
                "language": {"type": "string"},
                "available": {"type": "boolean"},
                "fallback_message": {"type": "string", "nullable": True},
                "error": {"type": "string", "nullable": True},
            },
        }

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        url = kwargs.get("url", "")
        video_id = kwargs.get("video_id") or extract_youtube_video_id(url)

        if not video_id:
            return {
                "transcript": "",
                "video_id": "",
                "language": "",
                "available": False,
                "fallback_message": "No valid YouTube URL or video ID provided.",
                "error": "Invalid YouTube URL",
            }

        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            try:
                transcript = transcript_list.find_transcript(["en"])
            except Exception:
                transcript = next(iter(transcript_list))

            fetched = transcript.fetch()
            full_text = " ".join(entry["text"] for entry in fetched)

            return {
                "transcript": full_text,
                "video_id": video_id,
                "language": transcript.language_code,
                "available": True,
                "fallback_message": None,
                "error": None,
            }
        except Exception as e:
            logger.warning("YouTube transcript unavailable for %s: %s", video_id, e)
            return {
                "transcript": "",
                "video_id": video_id,
                "language": "",
                "available": False,
                "fallback_message": (
                    f"Transcript unavailable for video {video_id}. "
                    "The video may not have captions enabled, or they may be restricted."
                ),
                "error": str(e),
            }
