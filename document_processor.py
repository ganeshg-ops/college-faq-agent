import os
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdf

from config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    CHUNK_SIZE_CHARS,
    CHUNK_OVERLAP_CHARS,
)


class DocumentProcessingError(Exception):
    """Custom exception raised during document extraction or validation."""
    pass


class DocumentProcessor:
    """
    Extracts, validates, and chunks text from approved college documents:
    PDF, TXT, CSV, and JSON.
    Preserves document names, page numbers, and section references.
    """

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE_CHARS,
        chunk_overlap: int = CHUNK_OVERLAP_CHARS,
        max_file_size_mb: int = MAX_FILE_SIZE_MB,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def validate_file(self, file_path: Path) -> None:
        """Validate file existence, extension, and file size."""
        if not file_path.exists():
            raise DocumentProcessingError(f"File not found: {file_path.name}")

        ext = file_path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise DocumentProcessingError(
                f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        file_size = file_path.stat().st_size
        if file_size > self.max_file_size_bytes:
            raise DocumentProcessingError(
                f"File '{file_path.name}' exceeds the maximum allowed size of {self.max_file_size_bytes // (1024*1024)}MB."
            )

        if file_size == 0:
            raise DocumentProcessingError(f"File '{file_path.name}' is empty (0 bytes).")

    def process_file(self, file_path: str | Path) -> List[Dict[str, Any]]:
        """
        Processes a single document and returns a list of indexed chunk dictionaries.
        Each chunk contains:
          - text: str
          - document_name: str
          - document_path: str
          - page: int or None
          - section: str
          - chunk_id: str
        """
        path = Path(file_path).resolve()
        self.validate_file(path)

        ext = path.suffix.lower()
        raw_sections: List[Dict[str, Any]] = []

        try:
            if ext == ".pdf":
                raw_sections = self._extract_pdf(path)
            elif ext == ".txt":
                raw_sections = self._extract_txt(path)
            elif ext == ".csv":
                raw_sections = self._extract_csv(path)
            elif ext == ".json":
                raw_sections = self._extract_json(path)
        except Exception as e:
            if isinstance(e, DocumentProcessingError):
                raise
            raise DocumentProcessingError(f"Error extracting content from '{path.name}': {str(e)}")

        if not raw_sections:
            raise DocumentProcessingError(f"No readable text content extracted from '{path.name}'.")

        # Create structured chunks with preserved provenance
        chunks = self._chunk_sections(raw_sections, path.name, str(path))
        return chunks

    def _extract_pdf(self, path: Path) -> List[Dict[str, Any]]:
        """Extract text page-by-page from PDF, preserving page numbers and headings."""
        sections = []
        reader = pypdf.PdfReader(str(path))

        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise DocumentProcessingError(f"PDF '{path.name}' is encrypted and cannot be read.")

        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if not text:
                continue

            # Heuristic to find section title from the first non-empty line
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            section_title = lines[0][:80] if lines else f"Page {page_idx}"

            sections.append({
                "page": page_idx,
                "section": section_title,
                "text": text,
            })
        return sections

    def _extract_txt(self, path: Path) -> List[Dict[str, Any]]:
        """Extract text from TXT file, splitting into logical sections based on headers."""
        text = ""
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                with open(path, "r", encoding=encoding) as f:
                    text = f.read()
                break
            except UnicodeDecodeError:
                continue

        text = text.strip()
        if not text:
            return []

        # Split on markdown headings or double newlines
        paragraphs = text.split("\n\n")
        sections = []
        current_header = "General Information"
        accumulated_text = []

        for p in paragraphs:
            clean_p = p.strip()
            if not clean_p:
                continue

            # Detect heading lines (e.g. # Header or SECTION: ...)
            first_line = clean_p.splitlines()[0].strip()
            if first_line.startswith(("#", "SECTION", "CHAPTER", "ARTICLE", "RULE")):
                if accumulated_text:
                    sections.append({
                        "page": None,
                        "section": current_header,
                        "text": "\n\n".join(accumulated_text),
                    })
                    accumulated_text = []
                current_header = first_line.lstrip("#").strip()[:80]
                accumulated_text.append(clean_p)
            else:
                accumulated_text.append(clean_p)

        if accumulated_text:
            sections.append({
                "page": None,
                "section": current_header,
                "text": "\n\n".join(accumulated_text),
            })

        return sections

    def _extract_csv(self, path: Path) -> List[Dict[str, Any]]:
        """Extract CSV rows, converting each row or category into readable formatted text."""
        sections = []
        encoding = "utf-8"
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    f.read(512)
                encoding = enc
                break
            except UnicodeDecodeError:
                continue

        with open(path, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            if not headers:
                return []

            for row_idx, row in enumerate(reader, start=1):
                # Format row into clean descriptive key-value text
                row_items = [f"{k.strip()}: {v.strip()}" for k, v in row.items() if k and v and v.strip()]
                if not row_items:
                    continue

                row_text = ", ".join(row_items)
                first_val = list(row.values())[0] if row.values() else f"Row {row_idx}"
                section_name = f"Row {row_idx} ({str(first_val)[:40]})"

                sections.append({
                    "page": None,
                    "section": section_name,
                    "text": row_text,
                })
        return sections

    def _extract_json(self, path: Path) -> List[Dict[str, Any]]:
        """Extract structured records from JSON files (lists of items, dicts, FAQs)."""
        sections = []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            for idx, item in enumerate(data, start=1):
                if isinstance(item, dict):
                    # Check for explicit title/category/question fields
                    section_title = (
                        item.get("title")
                        or item.get("topic")
                        or item.get("category")
                        or item.get("question")
                        or item.get("department")
                        or item.get("event")
                        or f"Record #{idx}"
                    )
                    text_parts = [f"{k}: {v}" for k, v in item.items() if v is not None]
                    text = "\n".join(text_parts)
                else:
                    section_title = f"Item #{idx}"
                    text = str(item)

                if text.strip():
                    sections.append({
                        "page": None,
                        "section": str(section_title)[:80],
                        "text": text.strip(),
                    })
        elif isinstance(data, dict):
            for key, val in data.items():
                section_title = str(key)[:80]
                if isinstance(val, (dict, list)):
                    text = json.dumps(val, indent=2, ensure_ascii=False)
                else:
                    text = f"{key}: {val}"

                if text.strip():
                    sections.append({
                        "page": None,
                        "section": section_title,
                        "text": text.strip(),
                    })
        else:
            sections.append({
                "page": None,
                "section": "Document Root",
                "text": str(data),
            })

        return sections

    def _chunk_sections(
        self, raw_sections: List[Dict[str, Any]], doc_name: str, doc_path: str
    ) -> List[Dict[str, Any]]:
        """Split raw sections into bounded chunks while preserving source metadata."""
        final_chunks = []
        chunk_counter = 1

        for sec in raw_sections:
            text = sec["text"]
            page = sec.get("page")
            section_name = sec.get("section", "General")

            # If section text fits in chunk_size, keep it intact
            if len(text) <= self.chunk_size:
                final_chunks.append({
                    "chunk_id": f"{doc_name}_{chunk_counter}",
                    "document_name": doc_name,
                    "document_path": doc_path,
                    "page": page,
                    "section": section_name,
                    "text": text,
                })
                chunk_counter += 1
            else:
                # Split with overlap respecting paragraph/sentence boundaries
                start = 0
                sub_idx = 1
                while start < len(text):
                    end = start + self.chunk_size
                    if end >= len(text):
                        chunk_slice = text[start:]
                    else:
                        # Attempt to find paragraph or sentence break
                        break_pos = text.rfind("\n", start, end)
                        if break_pos == -1 or break_pos < start + (self.chunk_size // 2):
                            break_pos = text.rfind(". ", start, end)
                        if break_pos != -1 and break_pos > start + (self.chunk_size // 2):
                            chunk_slice = text[start : break_pos + 1]
                            start = break_pos + 1
                        else:
                            chunk_slice = text[start:end]
                            start = end - self.chunk_overlap

                    clean_slice = chunk_slice.strip()
                    if clean_slice:
                        final_chunks.append({
                            "chunk_id": f"{doc_name}_{chunk_counter}_{sub_idx}",
                            "document_name": doc_name,
                            "document_path": doc_path,
                            "page": page,
                            "section": f"{section_name} (Part {sub_idx})" if sub_idx > 1 else section_name,
                            "text": clean_slice,
                        })
                        sub_idx += 1

                    if end >= len(text):
                        break
                chunk_counter += 1

        return final_chunks
