"""
extractor.py — Person 1: Document Extraction
Extracts plain text and preserves basic structural headers from PDF, DOCX, HTML, MD, and TXT.
"""

from pathlib import Path
from typing import Dict, Any
import re


class DocumentExtractor:
    """Multi-format document loader with graceful fallbacks."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".html", ".htm", ".md", ".markdown", ".txt"}

    def extract(self, file_path: str | Path) -> Dict[str, Any]:
        path = Path(file_path)
        ext = path.suffix.lower()

        if not path.exists():
            raise FileNotFoundError(f"Target document does not exist: {path}")

        if ext in (".txt", ""):
            return self._extract_txt(path)
        elif ext in (".md", ".markdown"):
            return self._extract_markdown(path)
        elif ext in (".html", ".htm"):
            return self._extract_html(path)
        elif ext == ".pdf":
            return self._extract_pdf(path)
        elif ext == ".docx":
            return self._extract_docx(path)
        else:
            return self._extract_txt(path)

    def _extract_txt(self, path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        return {"text": text, "format": "txt", "pages": 1}

    def _extract_markdown(self, path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        return {"text": text, "format": "markdown", "pages": 1}

    def _extract_html(self, path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw_html = f.read()

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw_html, "html.parser")
            for unwanted in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                unwanted.decompose()
            text = soup.get_text(separator="\n")
        except ImportError:
            text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", "\n", text)

        return {"text": text, "format": "html", "pages": 1}

    def _extract_pdf(self, path: Path) -> Dict[str, Any]:
        extracted_pages = []
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_pages.append(f"--- Page {i+1} ---\n" + page_text)
            text = "\n\n".join(extracted_pages)
            return {"text": text, "format": "pdf", "pages": len(reader.pages)}
        except ImportError:
            raise ImportError("To extract PDFs, install pypdf: pip install pypdf")

    def _extract_docx(self, path: Path) -> Dict[str, Any]:
        try:
            import docx
            doc = docx.Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n\n".join(paragraphs)
            return {"text": text, "format": "docx", "pages": 1}
        except ImportError:
            raise ImportError("To extract DOCX files, install python-docx: pip install python-docx")