from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from .base import BaseEvent, EventType


@dataclass
class RecommendationGeneratedEvent(BaseEvent):
    recommendation_id: int = None
    user_id: int = None
    recommendation_type: str = None
    title: str = None
    description: str = None
    recommended_action: str = None
    risk_level: str = None
    confidence_score: float = None
    model_used: str = None

    def __post_init__(self):
        self.event_type = EventType.RECOMMENDATION_GENERATED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "user_id": self.user_id,
            "recommendation_type": self.recommendation_type,
            "title": self.title,
            "description": self.description,
            "recommended_action": self.recommended_action,
            "risk_level": self.risk_level,
            "confidence_score": self.confidence_score,
            "model_used": self.model_used
        }


@dataclass
class InvestmentRecommendedEvent(BaseEvent):
    recommendation_id: int = None
    user_id: int = None
    investment_type: str = None
    asset_name: str = None
    asset_symbol: Optional[str] = None
    recommended_amount: float = None
    expected_return: float = None
    risk_level: str = None
    time_horizon: str = None
    is_shariah_compliant: bool = False
    country: Optional[str] = None
    reasoning: str = None

    def __post_init__(self):
        self.event_type = EventType.INVESTMENT_RECOMMENDED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "user_id": self.user_id,
            "investment_type": self.investment_type,
            "asset_name": self.asset_name,
            "asset_symbol": self.asset_symbol,
            "recommended_amount": self.recommended_amount,
            "expected_return": self.expected_return,
            "risk_level": self.risk_level,
            "time_horizon": self.time_horizon,
            "is_shariah_compliant": self.is_shariah_compliant,
            "country": self.country,
            "reasoning": self.reasoning
        }


@dataclass
class InsightGeneratedEvent(BaseEvent):
    insight_id: int = None
    user_id: int = None
    insight_type: str = None
    title: str = None
    message: str = None
    priority: str = "medium"
    is_urgent: bool = False
    supporting_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.event_type = EventType.INSIGHT_GENERATED

    def _get_data(self) -> Dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "user_id": self.user_id,
            "insight_type": self.insight_type,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "is_urgent": self.is_urgent,
            "supporting_data": self.supporting_data
        }
