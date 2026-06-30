"""PDF parser tool using PyMuPDF with OCR fallback."""

import logging
from pathlib import Path
from typing import Any

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class PDFParserTool(BaseTool):
    """Extract text from PDF files with OCR fallback for scanned pages."""

    name = "pdf_parser"
    description = (
        "Parse PDF documents and extract cleaned text. "
        "Falls back to OCR for scanned/image-based pages."
    )

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to PDF file"},
                "use_ocr_fallback": {"type": "boolean", "default": True},
            },
            "required": ["file_path"],
        }

    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "page_count": {"type": "integer"},
                "pages_with_ocr": {"type": "array", "items": {"type": "integer"}},
                "metadata": {"type": "object"},
                "error": {"type": "string", "nullable": True},
            },
        }

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        file_path = kwargs.get("file_path", "")
        use_ocr_fallback = kwargs.get("use_ocr_fallback", True)

        if not file_path or not Path(file_path).exists():
            return {
                "text": "",
                "page_count": 0,
                "pages_with_ocr": [],
                "metadata": {},
                "error": f"PDF file not found: {file_path}",
            }

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            pages_text: list[str] = []
            pages_with_ocr: list[int] = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").strip()

                if len(text) < 50 and use_ocr_fallback:
                    # Likely scanned page - use OCR fallback
                    temp_path = Path(file_path).parent / f"_ocr_page_{page_num}.png"
                    try:
                        from app.tools.ocr_tool import OCRTool

                        pix = page.get_pixmap(dpi=150)
                        pix.save(str(temp_path))

                        ocr_result = await OCRTool().run(file_path=str(temp_path))
                        text = ocr_result.get("text", "")
                        if text:
                            pages_with_ocr.append(page_num + 1)
                    except Exception as ocr_err:
                        logger.warning("OCR fallback failed for page %d: %s", page_num, ocr_err)
                    finally:
                        temp_path.unlink(missing_ok=True)

                if text:
                    pages_text.append(f"--- Page {page_num + 1} ---\n{text}")

            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
            }
            page_count = len(doc)
            doc.close()

            cleaned_text = self._clean_text("\n\n".join(pages_text))

            return {
                "text": cleaned_text,
                "page_count": page_count,
                "pages_with_ocr": pages_with_ocr,
                "metadata": metadata,
                "error": None,
            }
        except ImportError:
            return {
                "text": "",
                "page_count": 0,
                "pages_with_ocr": [],
                "metadata": {},
                "error": "PyMuPDF is not installed. Install with: pip install pymupdf",
            }
        except Exception as e:
            logger.exception("PDF parsing failed for %s", file_path)
            return {
                "text": "",
                "page_count": 0,
                "pages_with_ocr": [],
                "metadata": {},
                "error": f"PDF parsing failed: {e!s}",
            }

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean extracted PDF text."""
        import re

        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()
