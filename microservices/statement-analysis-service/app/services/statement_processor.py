"""Main statement-processing pipeline orchestrator."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.ai.transaction_extractor import TransactionExtractor
from app.categorization import confidence_scorer, rule_categorizer, vector_categorizer
from app.events import producer as event_producer
from app.services import chroma_service, redis_service, s3_service
from app.utils.exceptions import ParsingError, S3DownloadError, UnsupportedFileTypeError

logger = logging.getLogger(__name__)

_extractor = TransactionExtractor()
_MAX_CATEGORIZE_WORKERS = 8  # parallel workers for transaction categorization


def _categorize_one(raw: Dict, chroma) -> Dict:
    """Categorize a single transaction — safe to call from multiple threads (read-only chroma)."""
    cat_result = vector_categorizer.categorise(raw.get("description", ""), chroma)
    if cat_result is None:
        cat_result = rule_categorizer.categorise(
            raw.get("description", ""),
            raw.get("amount", 0.0),
            raw.get("category_hint"),
        )
    final_conf = confidence_scorer.combine(
        cat_result.get("confidence_score", 0.5),
        1.0,
        cat_result.get("categorization_method", "rule"),
    )
    cat_result["confidence_score"] = final_conf
    return {**raw, **cat_result}


def _get_parser(file_type: str):
    if file_type == "pdf":
        from app.parsers.pdf_parser import PDFParser
        return PDFParser()
    if file_type == "csv":
        from app.parsers.csv_parser import CSVParser
        return CSVParser()
    if file_type in ("excel", "xlsx", "xls"):
        from app.parsers.excel_parser import ExcelParser
        return ExcelParser()
    raise UnsupportedFileTypeError(f"Unsupported file type: {file_type}")


def process_statement(statement_data: Dict, processing_id: str) -> Dict:
    """Full pipeline: S3 download → parse → extract → categorise → publish.

    Updates Redis status throughout. Publishes Kafka events on completion/failure.
    """
    statement_id = statement_data.get("statement_id", "unknown")
    user_id = int(statement_data.get("user_id", 0))
    file_url = statement_data.get("file_url", "")
    start_time = time.time()

    def _update_status(status: str, progress: int, results: Dict = None, error: str = None):
        payload = {
            "statement_id": statement_id,
            "processing_id": processing_id,
            "status": status,
            "progress_percentage": progress,
            "started_at": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
            "completed_at": None,
            "processing_time_seconds": None,
            "results": results,
            "error": error,
        }
        redis_service.set_status(statement_id, payload)

    try:
        # ── 1. Download from S3 ───────────────────────────────────────────────
        _update_status("processing", 10)
        file_content = s3_service.download_statement(file_url)
        if file_content is None:
            raise S3DownloadError(f"Failed to download {file_url} from S3")

        # ── 2. Detect file type & parse ───────────────────────────────────────
        _update_status("processing", 25)
        file_type = s3_service.detect_file_type(file_url)
        parser = _get_parser(file_type)
        parsed_data = parser.parse(file_content)

        # ── 3. AI extraction ──────────────────────────────────────────────────
        _update_status("processing", 50)
        raw_txns = _extractor.extract(parsed_data)
        logger.info("Extracted %d raw transactions from %s", len(raw_txns), statement_id)

        # ── 4. Categorise — parallel across transactions ──────────────────────
        _update_status("processing", 70)
        chroma = chroma_service.get_client()
        categorised: List[Dict] = []
        conf_scores: List[float] = []

        n_workers = min(_MAX_CATEGORIZE_WORKERS, max(1, len(raw_txns)))
        results_map: Dict[int, Dict] = {}

        with ThreadPoolExecutor(max_workers=n_workers, thread_name_prefix="cat") as pool:
            futures = {pool.submit(_categorize_one, raw, chroma): idx
                       for idx, raw in enumerate(raw_txns)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results_map[idx] = future.result()
                except Exception as exc:
                    logger.error("Categorization failed txn=%d: %s", idx, exc)
                    results_map[idx] = {
                        **raw_txns[idx],
                        "category": "Other",
                        "confidence_score": 0.0,
                        "categorization_method": "fallback",
                    }

        # Restore original order, then do sequential post-processing
        for idx in range(len(raw_txns)):
            txn = results_map[idx]
            conf_scores.append(txn.get("confidence_score", 0.0))
            categorised.append(txn)

            # Publish per-transaction event (fire-and-forget)
            event_producer.publish_expense_categorized(user_id, statement_id, txn)

            # Store learned pattern in ChromaDB (write — must be sequential)
            vector_categorizer.add_pattern(
                txn.get("description", ""),
                txn.get("category", "Other"),
                txn.get("subcategory"),
                chroma,
            )

        # ── 5. Build result & publish completion ──────────────────────────────
        elapsed = int(time.time() - start_time)
        conf_counts = confidence_scorer.count_by_level(conf_scores)

        results = {
            "total_transactions": len(categorised),
            "successfully_extracted": len(categorised),
            "failed_extractions": 0,
            "categories_assigned": sum(1 for t in categorised if t.get("category")),
            "confidence_scores": conf_counts,
        }

        final_status = {
            "statement_id": statement_id,
            "processing_id": processing_id,
            "status": "completed",
            "progress_percentage": 100,
            "started_at": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
            "completed_at": datetime.now(tz=timezone.utc).isoformat(),
            "processing_time_seconds": elapsed,
            "results": results,
            "error": None,
        }
        redis_service.set_status(statement_id, final_status)

        event_producer.publish_statement_processed(user_id, statement_id, processing_id, categorised, results)
        logger.info("Statement %s processed in %ds — %d transactions", statement_id, elapsed, len(categorised))
        return final_status

    except Exception as exc:
        elapsed = int(time.time() - start_time)
        error_msg = str(exc)
        logger.error("Statement %s processing failed: %s", statement_id, error_msg)

        failed_status = {
            "statement_id": statement_id,
            "processing_id": processing_id,
            "status": "failed",
            "progress_percentage": 0,
            "started_at": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
            "completed_at": datetime.now(tz=timezone.utc).isoformat(),
            "processing_time_seconds": elapsed,
            "results": None,
            "error": error_msg,
        }
        redis_service.set_status(statement_id, failed_status)
        event_producer.publish_statement_failed(user_id, statement_id, processing_id, error_msg, elapsed)
        return failed_status
