import io
import logging
from typing import Dict, List

from app.parsers.base_parser import BaseParser
from app.utils.exceptions import ParsingError

logger = logging.getLogger(__name__)

# Maps common column name variations → canonical name
_DATE_KEYS = {"date", "transaction date", "posted date", "trans date", "post date"}
_DESC_KEYS = {"description", "merchant", "details", "memo", "narrative", "payee"}
_AMOUNT_KEYS = {"amount", "debit amount", "credit amount", "transaction amount"}
_TYPE_KEYS = {"type", "transaction type", "debit/credit", "dr/cr"}


class CSVParser(BaseParser):
    """Parse bank statements from CSV files."""

    def parse(self, file_content: bytes) -> Dict:
        try:
            import pandas as pd  # lazy import
        except ImportError as exc:
            raise ParsingError("pandas not installed. Run: pip install pandas") from exc

        try:
            df = self._load_df(pd, file_content)
            col_map = self._map_columns(list(df.columns))
            df = df.rename(columns=col_map)

            transactions: List[Dict] = []
            for _, row in df.iterrows():
                txn = {
                    "date": str(row.get("date", "")).strip(),
                    "description": str(row.get("description", "")).strip(),
                    "amount": self._clean_amount(row.get("amount")),
                    "transaction_type": self._detect_transaction_type(row.get("type")),
                }
                if txn["description"] and txn["amount"] > 0:
                    transactions.append(txn)

            return {
                "text": "",
                "transactions": transactions,
                "row_count": len(transactions),
                "metadata": {"columns": list(df.columns)},
            }
        except ParsingError:
            raise
        except Exception as exc:
            logger.error("CSV parse error: %s", exc)
            raise ParsingError(f"CSV parsing failed: {exc}") from exc

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load_df(pd, content: bytes):
        """Try multiple encodings until one works."""
        for enc in ("utf-8", "utf-8-sig", "latin-1", "iso-8859-1"):
            try:
                return pd.read_csv(io.StringIO(content.decode(enc)))
            except UnicodeDecodeError:
                continue
        raise ParsingError("CSV encoding detection failed for provided file content")

    @staticmethod
    def _map_columns(columns: List[str]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        cols_lower = [c.lower().strip() for c in columns]

        def _first_match(keys):
            for k in keys:
                if k in cols_lower:
                    return columns[cols_lower.index(k)]
            return None

        if col := _first_match(_DATE_KEYS):
            mapping[col] = "date"
        if col := _first_match(_DESC_KEYS):
            mapping[col] = "description"
        if col := _first_match(_AMOUNT_KEYS):
            mapping[col] = "amount"
        if col := _first_match(_TYPE_KEYS):
            mapping[col] = "type"

        return mapping
