"""
metadata_builder.py — Person 1: Metadata Enrichment
Assembles standardized JSON payload records for Person 2 (AQ Gen + Vector DB).
"""

from datetime import datetime, timezone
import hashlib
import re
from typing import List, Dict, Any
from chunker import RawChunk


class MetadataBuilder:
    def __init__(self, avg_chars_per_token: float = 3.85):
        self.avg_chars_per_token = avg_chars_per_token

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / self.avg_chars_per_token))

    def compute_sha256(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        words = re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{3,}\b", text.lower())
        stopwords = {
            "this", "that", "with", "from", "have", "more", "which", "their", "about",
            "there", "would", "these", "other", "into", "could", "first", "than", "then"
        }
        filtered = [w for w in words if w not in stopwords]
        freq: Dict[str, int] = {}
        for w in filtered:
            freq[w] = freq.get(w, 0) + 1
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:max_keywords]]

    def build_chunks_with_metadata(
        self,
        raw_chunks: List[RawChunk],
        doc_id: str,
        doc_name: str,
        source_format: str,
        cleaned_full_text: str,
        extra_meta: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        now_iso = datetime.now(timezone.utc).isoformat()
        total_chunks = len(raw_chunks)
        enriched: List[Dict[str, Any]] = []

        for idx, chunk in enumerate(raw_chunks):
            text = chunk.text.strip()
            content_hash = self.compute_sha256(text)
            tokens = self.estimate_tokens(text)
            keywords = self.extract_keywords(text)

            chunk_id = f"{doc_id}_chunk_{idx:04d}"
            current_header = chunk.header_breadcrumb[-1] if chunk.header_breadcrumb else ""

            # Standardized Contract for Person 2
            item = {
                "id": chunk_id,
                "text": text,
                "metadata": {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "chunk_index": idx,
                    "total_chunks": total_chunks,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "char_count": len(text),
                    "token_estimate": tokens,
                    "section_hierarchy": chunk.header_breadcrumb,
                    "current_header": current_header,
                    "content_hash_sha256": content_hash,
                    "language": "en",
                    "keywords": keywords,
                    "created_at": now_iso,
                    "source_format": source_format,
                    **(extra_meta or {})
                }
            }
            enriched.append(item)

        return enriched