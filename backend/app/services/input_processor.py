"""Input processing service."""

import logging
from typing import Any

from app.models.domain import InputType, ProcessedInput
from app.services.file_service import FileService
from app.utils.helpers import extract_youtube_urls

logger = logging.getLogger(__name__)


class InputProcessor:
    """Process and normalize user inputs."""

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    async def process(
        self,
        text: str = "",
        file_ids: list[str] | None = None,
    ) -> ProcessedInput:
        """Parse text and file references into normalized input."""
        file_ids = file_ids or []
        file_paths: list[str] = []
        file_types: list[str] = []
        youtube_urls = extract_youtube_urls(text)

        for fid in file_ids:
            meta = self.file_service.get_file(fid)
            if meta:
                file_paths.append(meta["stored_path"])
                file_types.append(meta["file_type"])
            else:
                logger.warning("File ID not found: %s", fid)

        input_type = self._determine_input_type(text, file_types)

        return ProcessedInput(
            text=text or None,
            file_paths=file_paths,
            file_types=file_types,
            youtube_urls=youtube_urls,
            input_type=input_type,
            metadata={"file_ids": file_ids},
        )

    @staticmethod
    def _determine_input_type(text: str, file_types: list[str]) -> InputType:
        has_text = bool(text and text.strip())
        has_files = bool(file_types)

        if has_text and has_files:
            return InputType.MIXED
        if len(file_types) > 1 or len(set(file_types)) > 1:
            return InputType.MIXED
        if file_types:
            type_map = {
                "image": InputType.IMAGE,
                "pdf": InputType.PDF,
                "audio": InputType.AUDIO,
            }
            return type_map.get(file_types[0], InputType.MIXED)
        return InputType.TEXT
