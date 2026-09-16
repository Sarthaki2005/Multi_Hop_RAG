"""
cleaner.py — Person 1: Text Cleaning & Normalization
Standardizes raw extractions into high-signal text suitable for vectorization.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
import re
import unicodedata


@dataclass
class CleaningConfig:
    normalize_unicode: bool = True
    collapse_whitespace: bool = True
    fix_hyphenated_linebreaks: bool = True
    remove_page_headers_footers: bool = True
    redact_pii: bool = False
    max_consecutive_newlines: int = 2


class TextCleaner:
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    PHONE_REGEX = re.compile(r"\+?\d{1,3}?[-.\s]?\(?\d{2,4}?\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
    PAGE_BANNER_REGEX = re.compile(r"^PAGE\s+\d+\s+OF\s+\d+.*?$", re.MULTILINE | re.IGNORECASE)
    DASH_PAGE_REGEX = re.compile(r"^---+\s*(?:Page|PAGE)\s*\d+.*?---+$", re.MULTILINE)

    def __init__(self, config: CleaningConfig = None):
        self.cfg = config or CleaningConfig()

    def clean(self, raw_text: str, doc_format: str = "txt") -> Dict[str, Any]:
        original_length = len(raw_text)
        text = raw_text
        applied_rules: List[str] = []

        # 1. Unicode NFKC normalization
        if self.cfg.normalize_unicode:
            text = unicodedata.normalize("NFKC", text)
            # Remove zero-width spaces and control characters (except \n and \t)
            text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f]", "", text)
            applied_rules.append("unicode_nfkc_normalization")

        # 2. PDF header/footer banner removal
        if self.cfg.remove_page_headers_footers and doc_format == "pdf":
            text = self.PAGE_BANNER_REGEX.sub("", text)
            text = self.DASH_PAGE_REGEX.sub("", text)
            applied_rules.append("page_banners_removed")

        # 3. Repair broken hyphenated words across linebreaks (e.g., 'trans-\nformation' -> 'transformation')
        if self.cfg.fix_hyphenated_linebreaks:
            text = re.sub(r"(\b[a-zA-Z]{2,})-\s*\n\s*([a-zA-Z]{2,}\b)", r"\1\2", text)
            applied_rules.append("hyphenated_linebreaks_joined")

        # 4. Standardize quotes and dashes
        text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
        text = text.replace("—", " - ").replace("–", " - ")

        # 5. Optional PII redaction
        if self.cfg.redact_pii:
            text = self.EMAIL_REGEX.sub("[EMAIL_REDACTED]", text)
            text = self.PHONE_REGEX.sub("[PHONE_REDACTED]", text)
            applied_rules.append("pii_redacted")

        # 6. Collapse redundant spaces and linebreaks
        if self.cfg.collapse_whitespace:
            text = re.sub(r"[\t\r\f\v ]+", " ", text)
            max_nl = "\n" * self.cfg.max_consecutive_newlines
            text = re.sub(r"\n{3,}", max_nl, text)
            lines = [line.strip() for line in text.split("\n")]
            text = "\n".join(lines).strip()
            applied_rules.append("whitespace_collapsed")

        cleaned_length = len(text)
        reduction_pct = round(((original_length - cleaned_length) / max(original_length, 1)) * 100, 2)

        return {
            "cleaned_text": text,
            "original_char_count": original_length,
            "cleaned_char_count": cleaned_length,
            "reduction_pct": reduction_pct,
            "applied_rules": applied_rules,
        }