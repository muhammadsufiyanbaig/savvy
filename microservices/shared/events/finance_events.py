from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseEvent, EventType


@dataclass
class ExpenseCreatedEvent(BaseEvent):
    expense_id: int = None
    user_id: int = None
    amount: float = None
    currency: str = "USD"
    category: str = None
    expense_type: str = None
    description: Optional[str] = None
    transaction_date: datetime = None
    is_recurring: bool = False

    def __post_init__(self):
        self.event_type = EventType.EXPENSE_CREATED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "expense_id": self.expense_id,
            "user_id": self.user_id,
            "amount": self.amount,
            "currency": self.currency,
            "category": self.category,
            "expense_type": self.expense_type,
            "description": self.description,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "is_recurring": self.is_recurring
        }


@dataclass
class ExpenseCategorizedEvent(BaseEvent):
    expense_id: int = None
    user_id: int = None
    old_category: Optional[str] = None
    new_category: str = None
    confidence_score: float = None
    is_auto_categorized: bool = True

    def __post_init__(self):
        self.event_type = EventType.EXPENSE_CATEGORIZED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "expense_id": self.expense_id,
            "user_id": self.user_id,
            "old_category": self.old_category,
            "new_category": self.new_category,
            "confidence_score": self.confidence_score,
            "is_auto_categorized": self.is_auto_categorized
        }


@dataclass
class SavingsGoalCreatedEvent(BaseEvent):
    goal_id: int = None
    user_id: int = None
    name: str = None
    goal_type: str = None
    target_amount: float = None
    current_amount: float = 0.0
    currency: str = "USD"
    target_date: Optional[datetime] = None

    def __post_init__(self):
        self.event_type = EventType.SAVINGS_GOAL_CREATED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "user_id": self.user_id,
            "name": self.name,
            "goal_type": self.goal_type,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "currency": self.currency,
            "target_date": self.target_date.isoformat() if self.target_date else None
        }


@dataclass
class SavingsDepositEvent(BaseEvent):
    transaction_id: int = None
    goal_id: int = None
    user_id: int = None
    amount: float = None
    new_total: float = None
    progress_percentage: float = None

    def __post_init__(self):
        self.event_type = EventType.SAVINGS_DEPOSIT

    def _get_data(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "goal_id": self.goal_id,
            "user_id": self.user_id,
            "amount": self.amount,
            "new_total": self.new_total,
            "progress_percentage": self.progress_percentage
        }


@dataclass
class BudgetExceededEvent(BaseEvent):
    budget_id: int = None
    user_id: int = None
    category: str = None
    allocated_amount: float = None
    spent_amount: float = None
    exceeded_by: float = None
    period: str = None

    def __post_init__(self):
        self.event_type = EventType.BUDGET_EXCEEDED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "budget_id": self.budget_id,
            "user_id": self.user_id,
            "category": self.category,
            "allocated_amount": self.allocated_amount,
            "spent_amount": self.spent_amount,
            "exceeded_by": self.exceeded_by,
            "period": self.period
        }
