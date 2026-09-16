#!/usr/bin/env python3
"""
pipeline.py — Person 1 Main Orchestrator
Usage:
  python pipeline.py --input document.pdf --chunk-size 600 --overlap 80 --output chunks.jsonl
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from extractor import DocumentExtractor
from cleaner import TextCleaner, CleaningConfig
from chunker import RecursiveCharacterChunker, MarkdownHeaderChunker, ChunkingConfig
from metadata_builder import MetadataBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Person1.Ingestion")


class IngestionPipeline:
    def __init__(
        self,
        cleaning_config: Optional[CleaningConfig] = None,
        chunking_config: Optional[ChunkingConfig] = None,
    ):
        self.extractor = DocumentExtractor()
        self.cleaner = TextCleaner(config=cleaning_config or CleaningConfig())
        self.chunking_config = chunking_config or ChunkingConfig(chunk_size=600, chunk_overlap=80)
        self.chunker = RecursiveCharacterChunker(config=self.chunking_config)
        self.md_chunker = MarkdownHeaderChunker(config=self.chunking_config)
        self.metadata_builder = MetadataBuilder()

    def process_file(self, file_path: str | Path) -> List[Dict[str, Any]]:
        path = Path(file_path)
        logger.info(f"==> Step 1: Extracting content from: {path.name}")
        extracted = self.extractor.extract(path)
        raw_text = extracted["text"]
        doc_format = extracted["format"]

        logger.info(f"==> Step 2: Cleaning text ({len(raw_text):,} raw chars)")
        cleaned_result = self.cleaner.clean(raw_text, doc_format=doc_format)
        cleaned_text = cleaned_result["cleaned_text"]

        logger.info(f"==> Step 3: Chunking ({self.chunking_config.strategy} strategy)")
        if doc_format in ("md", "markdown") and self.chunking_config.strategy == "markdown_headers":
            raw_chunks = self.md_chunker.split_text(cleaned_text)
        else:
            raw_chunks = self.chunker.split_text(cleaned_text)

        logger.info(f"==> Step 4: Metadata enrichment for Person 2")
        enriched_chunks = self.metadata_builder.build_chunks_with_metadata(
            raw_chunks=raw_chunks,
            doc_id=path.stem,
            doc_name=path.name,
            source_format=doc_format,
            cleaned_full_text=cleaned_text,
            extra_meta={"file_size_bytes": path.stat().st_size if path.exists() else len(raw_text)}
        )

        logger.info(f"✓ Completed Person 1 pipeline: {len(enriched_chunks)} chunks ready for Person 2.")
        return enriched_chunks

    def export_to_jsonl(self, chunks: List[Dict[str, Any]], output_path: str | Path) -> None:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "a", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        logger.info(f"✓ Saved {len(chunks)} chunks to {out_file.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Person 1: Document Ingestion Pipeline")
    parser.add_argument("--input", "-i", required=True, help="Input document (PDF, MD, TXT, HTML, DOCX)")
    parser.add_argument("--output", "-o", default="chunks_for_person2.jsonl", help="Output JSONL file")
    parser.add_argument("--chunk-size", type=int, default=600, help="Target chunk size in characters")
    parser.add_argument("--overlap", type=int, default=80, help="Chunk overlap in characters")
    parser.add_argument("--redact-pii", action="store_true", help="Redact email and phone numbers")

    args = parser.parse_args()

    clean_cfg = CleaningConfig(redact_pii=args.redact_pii)
    chunk_cfg = ChunkingConfig(chunk_size=args.chunk_size, chunk_overlap=args.overlap)

    pipeline = IngestionPipeline(cleaning_config=clean_cfg, chunking_config=chunk_cfg)
    chunks = pipeline.process_file(args.input)
    pipeline.export_to_jsonl(chunks, args.output)


if __name__ == "__main__":
    main()