"""File upload and storage service."""

import logging
import uuid
from pathlib import Path

import aiofiles

from app.config.settings import Settings, get_settings
from app.utils.helpers import detect_file_type

logger = logging.getLogger(__name__)


class FileService:
    """Handle file uploads and retrieval."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._files: dict[str, dict] = {}
        self.upload_dir = self.settings.upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(
        self, filename: str, content: bytes, content_type: str | None = None
    ) -> dict:
        """Save uploaded file and return metadata."""
        if len(content) > self.settings.max_upload_bytes:
            raise ValueError(
                f"File exceeds maximum size of {self.settings.max_upload_size_mb}MB"
            )

        file_id = str(uuid.uuid4())
        ext = Path(filename).suffix
        stored_name = f"{file_id}{ext}"
        file_path = self.upload_dir / stored_name

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        file_type = detect_file_type(filename, content_type)
        metadata = {
            "file_id": file_id,
            "filename": filename,
            "stored_path": str(file_path),
            "content_type": content_type or "application/octet-stream",
            "size_bytes": len(content),
            "file_type": file_type,
        }
        self._files[file_id] = metadata
        logger.info("Saved file %s as %s (%s)", filename, file_id, file_type)
        return metadata

    def get_file(self, file_id: str) -> dict | None:
        return self._files.get(file_id)

    def get_file_path(self, file_id: str) -> str | None:
        meta = self._files.get(file_id)
        return meta["stored_path"] if meta else None

    def list_files(self) -> list[dict]:
        return list(self._files.values())


_file_service: FileService | None = None


def get_file_service() -> FileService:
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service
