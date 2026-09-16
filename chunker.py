"""
chunker.py — Person 1: Chunking Engine
Splits cleaned text into bounded passages while retaining overlap and section breadcrumbs.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import re


@dataclass
class ChunkingConfig:
    chunk_size: int = 600          # Target character length (~150 tokens)
    chunk_overlap: int = 80        # Overlap stride (~20 tokens)
    strategy: str = "recursive"    # 'recursive' or 'markdown_headers'
    separators: List[str] = field(
        default_factory=lambda: ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]
    )
    min_chunk_size: int = 50


@dataclass
class RawChunk:
    text: str
    start_char: int
    end_char: int
    header_breadcrumb: List[str] = field(default_factory=list)


class RecursiveCharacterChunker:
    """Prioritizes paragraph breaks (\n\n), then sentences (\n, .), then words."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.cfg = config or ChunkingConfig()

    def split_text(self, text: str) -> List[RawChunk]:
        if not text or not text.strip():
            return []

        raw_splits = self._split_recursive(text, self.cfg.separators)
        chunks: List[RawChunk] = []
        current_doc = []
        current_len = 0
        char_cursor = 0

        for piece in raw_splits:
            piece_len = len(piece)
            if current_len + piece_len > self.cfg.chunk_size and current_doc:
                merged_text = "".join(current_doc).strip()
                if len(merged_text) >= self.cfg.min_chunk_size:
                    start_idx = text.find(merged_text, max(0, char_cursor - self.cfg.chunk_overlap - 50))
                    if start_idx == -1:
                        start_idx = char_cursor
                    end_idx = start_idx + len(merged_text)
                    char_cursor = end_idx

                    chunks.append(RawChunk(
                        text=merged_text,
                        start_char=start_idx,
                        end_char=end_idx,
                        header_breadcrumb=[]
                    ))

                # Retain overlap from the tail of current_doc
                overlap_accum = []
                overlap_len = 0
                for item in reversed(current_doc):
                    if overlap_len + len(item) <= self.cfg.chunk_overlap:
                        overlap_accum.insert(0, item)
                        overlap_len += len(item)
                    else:
                        break
                current_doc = overlap_accum
                current_len = overlap_len

            current_doc.append(piece)
            current_len += piece_len

        if current_doc:
            merged_text = "".join(current_doc).strip()
            if len(merged_text) >= self.cfg.min_chunk_size:
                start_idx = text.find(merged_text, max(0, char_cursor - 50))
                if start_idx == -1:
                    start_idx = char_cursor
                chunks.append(RawChunk(
                    text=merged_text,
                    start_char=start_idx,
                    end_char=start_idx + len(merged_text),
                    header_breadcrumb=[]
                ))

        return chunks

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        separator = separators[-1]
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator != "" else list(text)
        final_pieces = []

        for s in splits:
            piece = s + separator if separator != "" and s != "" else s
            if len(piece) <= self.cfg.chunk_size or not new_separators:
                final_pieces.append(piece)
            else:
                final_pieces.extend(self._split_recursive(piece, new_separators))

        return final_pieces


class MarkdownHeaderChunker:
    """Splits along Markdown header boundaries (# H1, ## H2, ### H3) while maintaining breadcrumbs."""

    HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.cfg = config or ChunkingConfig()
        self.sub_chunker = RecursiveCharacterChunker(self.cfg)

    def split_text(self, markdown_text: str) -> List[RawChunk]:
        matches = list(self.HEADER_PATTERN.finditer(markdown_text))
        if not matches:
            return self.sub_chunker.split_text(markdown_text)

        sections = []
        breadcrumbs: dict = {}

        if matches[0].start() > 0:
            preamble = markdown_text[:matches[0].start()].strip()
            if preamble:
                sections.append((preamble, ["Overview"]))

        for i, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()

            breadcrumbs = {lvl: t for lvl, t in breadcrumbs.items() if lvl < level}
            breadcrumbs[level] = title
            hierarchy = [breadcrumbs[k] for k in sorted(breadcrumbs.keys())]

            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
            section_content = markdown_text[start_pos:end_pos].strip()

            sections.append((section_content, hierarchy))

        final_chunks: List[RawChunk] = []
        for content, hierarchy in sections:
            if len(content) <= self.cfg.chunk_size:
                start_idx = max(0, markdown_text.find(content))
                final_chunks.append(RawChunk(
                    text=content,
                    start_char=start_idx,
                    end_char=start_idx + len(content),
                    header_breadcrumb=hierarchy
                ))
            else:
                sub_chunks = self.sub_chunker.split_text(content)
                for sc in sub_chunks:
                    sc.header_breadcrumb = hierarchy
                    final_chunks.append(sc)

        return final_chunks