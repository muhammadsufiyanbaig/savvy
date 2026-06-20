from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator


# ── Requests ──────────────────────────────────────────────────────────────────

class RecommendationRequest(BaseModel):
    user_id: int
    recommendation_types: List[str] = ["savings", "spending", "budget"]
    context: Dict[str, Any] = {}


class SpendingAnalysisRequest(BaseModel):
    user_id: int
    period: str = "last_3_months"
    expenses: Optional[List[Dict[str, Any]]] = None


class FeedbackRequest(BaseModel):
    rating: int
    was_helpful: bool
    feedback_text: Optional[str] = None
    is_implemented: bool = False

    @field_validator("rating")
    @classmethod
    def valid_rating(cls, v: int) -> int:
        if v not in range(1, 6):
            raise ValueError("rating must be 1–5")
        return v


# ── Response objects ──────────────────────────────────────────────────────────

class Recommendation(BaseModel):
    id: str
    type: str
    title: str
    description: str
    recommended_action: str
    expected_benefit: str
    risk_level: str = "low"
    confidence_score: float = 0.0
    priority: str = "medium"


class RecommendationResponse(BaseModel):
    recommendations: List[Recommendation]
    generated_at: str
    model_used: str = "rule-based"
    total_count: int


class SpendingCategory(BaseModel):
    category: str
    amount: float
    percentage: float


class SpendingAnalysis(BaseModel):
    top_categories: List[SpendingCategory] = []
    spending_trend: str = "stable"
    month_over_month_change: float = 0.0
    vs_similar_users: str = ""
    biggest_opportunity: str = ""
    score: int = 70
    score_label: str = "Good"


class SpendingAnalysisResponse(BaseModel):
    analysis: SpendingAnalysis


class FeedbackResponse(BaseModel):
    recommendation_id: str
    feedback_recorded: bool
    message: str


class Insight(BaseModel):
    id: str
    type: str
    title: str
    message: str
    priority: str = "medium"
    is_urgent: bool = False
    supporting_data: Dict[str, Any] = {}


class InsightsResponse(BaseModel):
    insights: List[Insight]
    generated_at: str
    total_count: int
