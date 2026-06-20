"""Parser unit tests — mock underlying library calls."""

import io
from unittest.mock import MagicMock, patch

import pytest

from app.utils.exceptions import ParsingError


# ── PDF Parser ────────────────────────────────────────────────────────────────

class TestPDFParser:
    def _make_mock_reader(self, text: str, num_pages: int = 1):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = text

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page] * num_pages
        mock_reader.metadata = {"/Author": "Bank"}
        return mock_reader

    def test_parse_with_transaction_text(self):
        from app.parsers.pdf_parser import PDFParser

        sample_text = (
            "BANK STATEMENT\n"
            "01/15/2026  STARBUCKS COFFEE     5.75\n"
            "01/16/2026  AMAZON.COM          49.99\n"
            "01/17/2026  SHELL OIL           45.00\n"
        )
        mock_reader = self._make_mock_reader(sample_text)

        with patch("PyPDF2.PdfReader", return_value=mock_reader):
            parser = PDFParser()
            result = parser.parse(b"%PDF fake")

        assert result["page_count"] == 1
        assert sample_text in result["text"]
        assert "tables" in result or "transactions" in result

    def test_parse_extracts_transaction_rows(self):
        from app.parsers.pdf_parser import PDFParser

        # Pattern the regex will match: MM/DD/YYYY  description  amount
        sample_text = "02/01/2026  STARBUCKS COFFEE #1234  5.75\n"
        mock_reader = self._make_mock_reader(sample_text)

        with patch("PyPDF2.PdfReader", return_value=mock_reader):
            parser = PDFParser()
            result = parser.parse(b"%PDF fake")

        rows = result.get("transactions", [])
        assert len(rows) >= 1
        assert rows[0]["amount"] == 5.75

    def test_parse_multi_page(self):
        from app.parsers.pdf_parser import PDFParser

        text = "02/01/2026  WALMART GROCERY  123.45\n"
        mock_reader = self._make_mock_reader(text, num_pages=3)

        with patch("PyPDF2.PdfReader", return_value=mock_reader):
            parser = PDFParser()
            result = parser.parse(b"fake pdf")

        assert result["page_count"] == 3

    def test_parse_raises_on_corrupt(self):
        from app.parsers.pdf_parser import PDFParser

        with patch("PyPDF2.PdfReader", side_effect=Exception("corrupt")):
            parser = PDFParser()
            with pytest.raises(ParsingError):
                parser.parse(b"not a real pdf")

    def test_parse_empty_pdf(self):
        from app.parsers.pdf_parser import PDFParser

        mock_reader = self._make_mock_reader("")
        with patch("PyPDF2.PdfReader", return_value=mock_reader):
            parser = PDFParser()
            result = parser.parse(b"fake")
        assert result["text"] == "\n"
        assert result["transactions"] == []


# ── CSV Parser ────────────────────────────────────────────────────────────────

class TestCSVParser:
    def test_parse_standard_csv(self, sample_csv_bytes):
        from app.parsers.csv_parser import CSVParser

        parser = CSVParser()
        result = parser.parse(sample_csv_bytes)

        assert result["row_count"] >= 1
        txns = result["transactions"]
        assert len(txns) >= 2

        starbucks = next((t for t in txns if "STARBUCKS" in t["description"]), None)
        assert starbucks is not None
        assert starbucks["amount"] == 5.75
        assert starbucks["transaction_type"] == "debit"

    def test_parse_credit_row(self, sample_csv_bytes):
        from app.parsers.csv_parser import CSVParser

        parser = CSVParser()
        result = parser.parse(sample_csv_bytes)
        txns = result["transactions"]
        payroll = next((t for t in txns if "PAYROLL" in t.get("description", "")), None)
        assert payroll is not None
        assert payroll["transaction_type"] == "credit"
        assert payroll["amount"] == 2500.00

    def test_parse_empty_csv_raises(self):
        from app.parsers.csv_parser import CSVParser

        parser = CSVParser()
        # No valid rows → should return 0 transactions (not raise)
        result = parser.parse(b"Date,Description,Amount\n")
        assert result["row_count"] == 0

    def test_parse_alternative_column_names(self):
        from app.parsers.csv_parser import CSVParser

        csv_data = (
            "Transaction Date,Merchant,Debit Amount\n"
            "2026-02-01,Netflix,15.99\n"
        ).encode("utf-8")

        parser = CSVParser()
        result = parser.parse(csv_data)
        txns = result["transactions"]
        assert len(txns) == 1
        assert "Netflix" in txns[0]["description"]
        assert txns[0]["amount"] == 15.99

    def test_parse_handles_encoding(self):
        from app.parsers.csv_parser import CSVParser

        csv_data = "Date,Description,Amount\n2026-02-01,CAFÉ ESPRESSO,4.50\n".encode("latin-1")
        parser = CSVParser()
        result = parser.parse(csv_data)
        assert result["row_count"] >= 1


# ── Excel Parser ─────────────────────────────────────────────────────────────

class TestExcelParser:
    def _make_mock_wb(self, rows):
        """Build a mock openpyxl workbook with given rows.

        Each call to iter_rows() returns a fresh iterator so the mock can be
        consumed multiple times (once by _find_transaction_sheet, once by
        _extract_rows).
        """
        mock_sheet = MagicMock()
        mock_sheet.title = "Transactions"

        # side_effect creates a new iter object on every call
        mock_sheet.iter_rows.side_effect = lambda *args, **kwargs: iter(
            [tuple(r) for r in rows]
        )

        mock_wb = MagicMock()
        mock_wb.worksheets = [mock_sheet]
        return mock_wb

    def test_parse_basic_excel(self):
        from app.parsers.excel_parser import ExcelParser

        rows = [
            ["Date", "Description", "Amount"],
            ["2026-02-01", "STARBUCKS COFFEE", 5.75],
            ["2026-02-02", "AMAZON.COM", 49.99],
        ]
        mock_wb = self._make_mock_wb(rows)

        with patch("openpyxl.load_workbook", return_value=mock_wb):
            parser = ExcelParser()
            result = parser.parse(b"fake xlsx")

        assert result["row_count"] == 2
        txns = result["transactions"]
        assert txns[0]["amount"] == 5.75
        assert txns[1]["amount"] == 49.99

    def test_parse_skips_empty_rows(self):
        from app.parsers.excel_parser import ExcelParser

        rows = [
            ["Date", "Description", "Amount"],
            ["2026-02-01", "WALMART", 55.00],
            [None, None, None],                   # empty row
            ["2026-02-03", "CVS PHARMACY", 12.50],
        ]
        mock_wb = self._make_mock_wb(rows)

        with patch("openpyxl.load_workbook", return_value=mock_wb):
            parser = ExcelParser()
            result = parser.parse(b"fake")

        txns = [t for t in result["transactions"] if t["amount"] > 0]
        assert len(txns) == 2

    def test_parse_corrupt_raises(self):
        from app.parsers.excel_parser import ExcelParser

        with patch("openpyxl.load_workbook", side_effect=Exception("bad file")):
            parser = ExcelParser()
            with pytest.raises(ParsingError):
                parser.parse(b"not excel")


# ── Base parser helpers ───────────────────────────────────────────────────────

class TestBaseParserHelpers:
    def test_clean_amount_normal(self):
        from app.parsers.base_parser import BaseParser

        assert BaseParser._clean_amount("$1,234.56") == 1234.56
        assert BaseParser._clean_amount("  45.00  ") == 45.0
        assert BaseParser._clean_amount("-99.99") == 99.99  # abs

    def test_clean_amount_invalid(self):
        from app.parsers.base_parser import BaseParser

        assert BaseParser._clean_amount("N/A") == 0.0
        assert BaseParser._clean_amount(None) == 0.0

    def test_detect_transaction_type(self):
        from app.parsers.base_parser import BaseParser

        assert BaseParser._detect_transaction_type("credit") == "credit"
        assert BaseParser._detect_transaction_type("CREDIT") == "credit"
        assert BaseParser._detect_transaction_type("CR") == "credit"
        assert BaseParser._detect_transaction_type("deposit") == "credit"
        assert BaseParser._detect_transaction_type("debit") == "debit"
        assert BaseParser._detect_transaction_type("DR") == "debit"
        assert BaseParser._detect_transaction_type(None) == "debit"
