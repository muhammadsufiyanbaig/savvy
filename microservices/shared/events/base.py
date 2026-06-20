from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum
import uuid
import json


class EventType(str, Enum):
    # User Events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_VERIFICATION_REQUESTED = "user.verification_requested"

    # Expense Events
    EXPENSE_CREATED = "expense.created"
    EXPENSE_UPDATED = "expense.updated"
    EXPENSE_DELETED = "expense.deleted"
    EXPENSE_CATEGORIZED = "expense.categorized"

    # Savings Events
    SAVINGS_GOAL_CREATED = "savings_goal.created"
    SAVINGS_GOAL_UPDATED = "savings_goal.updated"
    SAVINGS_GOAL_COMPLETED = "savings_goal.completed"
    SAVINGS_DEPOSIT = "savings.deposit"
    SAVINGS_WITHDRAWAL = "savings.withdrawal"

    # Bank Events
    BANK_ACCOUNT_ADDED = "bank_account.added"
    BANK_ACCOUNT_UPDATED = "bank_account.updated"
    BANK_STATEMENT_UPLOADED = "bank_statement.uploaded"
    BANK_STATEMENT_PROCESSED = "bank_statement.processed"
    BANK_STATEMENT_FAILED = "bank_statement.failed"

    # Budget Events
    BUDGET_CREATED = "budget.created"
    BUDGET_UPDATED = "budget.updated"
    BUDGET_EXCEEDED = "budget.exceeded"
    SPENDING_LIMIT_REACHED = "spending_limit.reached"

    # AI Events
    RECOMMENDATION_GENERATED = "recommendation.generated"
    INVESTMENT_RECOMMENDED = "investment.recommended"
    INSIGHT_GENERATED = "insight.generated"

    # Zakat Events
    ZAKAT_CALCULATED = "zakat.calculated"
    ZAKAT_PAID = "zakat.paid"
    QURBANI_GOAL_CREATED = "qurbani.goal_created"

    # Notification Events
    NOTIFICATION_SEND = "notification.send"
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"


@dataclass
class BaseEvent:
    """Base class for all events in the system"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    user_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value if self.event_type else None,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "metadata": self.metadata,
            "data": self._get_data()
        }

    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)

    def _get_data(self) -> Dict[str, Any]:
        """Get event-specific data - to be overridden by subclasses"""
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create event from dictionary"""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str):
        """Create event from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
