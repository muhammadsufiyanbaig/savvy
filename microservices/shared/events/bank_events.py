from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
from .base import BaseEvent, EventType


@dataclass
class BankAccountAddedEvent(BaseEvent):
    account_id: int = None
    user_id: int = None
    bank_name: str = None
    account_name: str = None
    account_type: str = None
    balance: float = 0.0
    currency: str = "USD"
    purpose: Optional[str] = None

    def __post_init__(self):
        self.event_type = EventType.BANK_ACCOUNT_ADDED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "user_id": self.user_id,
            "bank_name": self.bank_name,
            "account_name": self.account_name,
            "account_type": self.account_type,
            "balance": self.balance,
            "currency": self.currency,
            "purpose": self.purpose
        }


@dataclass
class BankStatementUploadedEvent(BaseEvent):
    statement_id: int = None
    user_id: int = None
    account_id: int = None
    file_name: str = None
    file_path: str = None
    file_type: str = None
    file_size: int = None
    statement_period_start: Optional[datetime] = None
    statement_period_end: Optional[datetime] = None

    def __post_init__(self):
        self.event_type = EventType.BANK_STATEMENT_UPLOADED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "statement_period_start": self.statement_period_start.isoformat() if self.statement_period_start else None,
            "statement_period_end": self.statement_period_end.isoformat() if self.statement_period_end else None
        }


@dataclass
class BankStatementProcessedEvent(BaseEvent):
    statement_id: int = None
    user_id: int = None
    account_id: int = None
    total_transactions: int = 0
    total_income: float = 0.0
    total_expenses: float = 0.0
    categorization_confidence: float = None
    extracted_expenses: List[Dict[str, Any]] = None

    def __post_init__(self):
        self.event_type = EventType.BANK_STATEMENT_PROCESSED
        if self.extracted_expenses is None:
            self.extracted_expenses = []

    def _get_data(self) -> Dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "total_transactions": self.total_transactions,
            "total_income": self.total_income,
            "total_expenses": self.total_expenses,
            "categorization_confidence": self.categorization_confidence,
            "extracted_expenses": self.extracted_expenses
        }


@dataclass
class BankStatementFailedEvent(BaseEvent):
    statement_id: int = None
    user_id: int = None
    account_id: int = None
    error_message: str = None
    error_type: str = None

    def __post_init__(self):
        self.event_type = EventType.BANK_STATEMENT_FAILED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "error_message": self.error_message,
            "error_type": self.error_type
        }
