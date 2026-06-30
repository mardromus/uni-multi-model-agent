"""YouTube transcript extraction tool."""

import logging
from typing import Any

from app.tools.base import BaseTool
from app.utils.helpers import extract_youtube_video_id

logger = logging.getLogger(__name__)


def parse_vtt(file_path: str) -> str:
    import os
    import re

    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    cleaned_lines = []
    seen = set()
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if (
            line_str.startswith("WEBVTT")
            or line_str.startswith("Kind:")
            or line_str.startswith("Language:")
            or line_str.startswith("Style:")
        ):
            continue
        if "-->" in line_str:
            continue
        line_str = re.sub(r"<[^>]+>", "", line_str).strip()
        if not line_str:
            continue
        if line_str not in seen:
            cleaned_lines.append(line_str)
            seen.add(line_str)
    return " ".join(cleaned_lines)


def parse_srt(file_path: str) -> str:
    import os
    import re

    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    cleaned_lines = []
    seen = set()
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if line_str.isdigit():
            continue
        if "-->" in line_str:
            continue
        line_str = re.sub(r"<[^>]+>", "", line_str).strip()
        if not line_str:
            continue
        if line_str not in seen:
            cleaned_lines.append(line_str)
            seen.add(line_str)
    return " ".join(cleaned_lines)


class YouTubeTool(BaseTool):
    """Fetch YouTube video transcripts with robust three-tier fallbacks."""

    name = "youtube"
    description = (
        "Detect and fetch YouTube video transcripts. "
        "Returns transcript text or graceful fallbacks (scrapers + Whisper) if blocked."
    )

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "YouTube video URL"},
                "video_id": {
                    "type": "string",
                    "description": "YouTube video ID (alternative to url)",
                },
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

        # TIER 1: Try youtube-transcript-api (fast, standard)
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
        except Exception as e1:
            logger.info(
                "Tier 1 youtube-transcript-api failed: %s. Trying Tier 2 (yt-dlp subtitles)...",
                e1,
            )

        # TIER 2: Try yt-dlp subtitle download (fast, bypasses blocks)
        try:
            import glob
            import os
            import tempfile
            import yt_dlp

            temp_dir = tempfile.gettempdir()
            out_base = os.path.join(temp_dir, f"yt_subs_{video_id}")

            # Clean up old files first if any
            for old_file in glob.glob(out_base + "*"):
                try:
                    os.remove(old_file)
                except Exception:
                    pass

            ydl_opts = {
                "writeautomaticsubtitles": True,
                "writesubtitles": True,
                "subtitleslangs": ["en"],
                "skip_download": True,
                "outtmpl": out_base,
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            files = glob.glob(out_base + "*")
            vtt_file = None
            for f in files:
                if f.endswith((".vtt", ".srt")):
                    vtt_file = f
                    break

            if vtt_file:
                if vtt_file.endswith(".srt"):
                    full_text = parse_srt(vtt_file)
                else:
                    full_text = parse_vtt(vtt_file)

                # Cleanup
                try:
                    os.remove(vtt_file)
                except Exception:
                    pass

                if full_text.strip():
                    return {
                        "transcript": full_text,
                        "video_id": video_id,
                        "language": "en",
                        "available": True,
                        "fallback_message": None,
                        "error": None,
                    }
            logger.info(
                "Tier 2 yt-dlp subtitles not found or empty. Trying Tier 3 (yt-dlp audio download + Whisper)..."
            )
        except Exception as e2:
            logger.warning("Tier 2 yt-dlp subtitles failed: %s. Trying Tier 3...", e2)

        # TIER 3: Try yt-dlp audio download + Whisper transcription (bulletproof fallback)
        try:
            import glob
            import os
            import tempfile
            import yt_dlp
            from app.tools.audio_tool import AudioTool

            temp_dir = tempfile.gettempdir()
            audio_out_tmpl = os.path.join(temp_dir, f"yt_audio_{video_id}")

            # Clean up old files first if any
            for old_file in glob.glob(audio_out_tmpl + "*"):
                try:
                    os.remove(old_file)
                except Exception:
                    pass

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": audio_out_tmpl + ".%(ext)s",
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            audio_files = glob.glob(audio_out_tmpl + "*")
            audio_file = None
            for f in audio_files:
                if not f.endswith((".lock", ".part")):
                    audio_file = f
                    break

            if audio_file:
                # Use our Whisper AudioTool
                audio_tool = AudioTool()
                transcribe_result = await audio_tool.run(file_path=audio_file)

                # Cleanup
                try:
                    os.remove(audio_file)
                except Exception:
                    pass

                if transcribe_result.get("error"):
                    raise RuntimeError(transcribe_result["error"])

                full_text = transcribe_result.get("transcript", "")
                if full_text.strip():
                    return {
                        "transcript": full_text,
                        "video_id": video_id,
                        "language": transcribe_result.get("language", "en"),
                        "available": True,
                        "fallback_message": None,
                        "error": None,
                    }
        except Exception as e3:
            logger.error("Tier 3 audio transcription failed: %s", e3)

        return {
            "transcript": "",
            "video_id": video_id,
            "language": "",
            "available": False,
            "fallback_message": (
                f"Transcript completely unavailable for video {video_id}. "
                "Unable to scrape subtitles or transcribe audio track."
            ),
            "error": "All transcription tiers failed",
        }
