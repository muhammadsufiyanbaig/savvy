import io
import re
import logging
from typing import Dict, List

from app.parsers.base_parser import BaseParser
from app.utils.exceptions import ParsingError

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF"

# Tags and injection markers to strip from extracted PDF text
_HTML_TAGS = re.compile(r'<[^>]{0,200}>')
_INJECTION_MARKERS = re.compile(
    r'(?i)(system\s*:|<\s*/?system\s*>|instructions?\s*:|ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?'
    r'|new\s+system\s+prompt|disregard\s+(?:all|previous)|your\s+actual\s+instructions)',
    re.I,
)
_INVISIBLE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')


class PDFParser(BaseParser):
    """Extract text and transaction rows from a bank-statement PDF."""

    # Common date-amount patterns in bank statement text
    _ROW_PATTERN = re.compile(
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"   # date
        r"\s+(.+?)\s+"                             # description
        r"([\d,]+\.\d{2})"                         # amount
        r"(?:\s+([\d,]+\.\d{2}))?",               # optional balance
        re.MULTILINE,
    )

    def parse(self, file_content: bytes) -> Dict:
        # Validate PDF magic bytes — reject non-PDF content before parsing
        if not file_content[:4] == _PDF_MAGIC:
            raise ParsingError("File does not appear to be a valid PDF (bad magic bytes)")

        # Enforce size cap — PDFs should not exceed 10 MB for bank statements
        max_bytes = 10 * 1024 * 1024
        if len(file_content) > max_bytes:
            raise ParsingError(f"PDF exceeds maximum allowed size of {max_bytes // (1024*1024)} MB")

        try:
            from PyPDF2 import PdfReader
        except ImportError as exc:
            raise ParsingError("PyPDF2 not installed. Run: pip install PyPDF2") from exc

        try:
            reader = PdfReader(io.BytesIO(file_content))

            full_text = ""
            for page in reader.pages:
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"

            # Sanitise extracted text before it enters any AI prompt
            full_text = self._sanitise_text(full_text)

            raw_rows = self._extract_rows(full_text)

            return {
                "text": full_text,
                "transactions": raw_rows,
                "page_count": len(reader.pages),
                # Strip PDF metadata — can contain injected instructions
                "metadata": {},
            }
        except ParsingError:
            raise
        except Exception as exc:
            logger.error("PDF parse error: %s", exc)
            raise ParsingError(f"PDF parsing failed: {exc}") from exc

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _sanitise_text(text: str) -> str:
        """Strip control chars, HTML tags, and known injection markers from PDF text."""
        # Remove control characters
        text = _INVISIBLE.sub('', text)
        # Remove HTML/XML tags (common in e-statement PDFs)
        text = _HTML_TAGS.sub(' ', text)
        # Replace injection markers with a safe placeholder
        text = _INJECTION_MARKERS.sub('[REMOVED]', text)
        return text

    def _extract_rows(self, text: str) -> List[Dict]:
        """Regex scan for transaction rows in plain text."""
        rows: List[Dict] = []
        for match in self._ROW_PATTERN.finditer(text):
            rows.append(
                {
                    "date": match.group(1).strip(),
                    "description": match.group(2).strip(),
                    "amount": self._clean_amount(match.group(3)),
                    "transaction_type": "debit",
                }
            )
        return rows
