from typing import Dict, List, Optional
from pydantic import BaseModel, field_validator


# ── Requests ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    statement_id: str
    file_url: str           # s3://bucket/key  OR  just the S3 key
    user_id: int
    bank_name: Optional[str] = None
    account_last_four: Optional[str] = None


class CategorizeRequest(BaseModel):
    description: str
    amount: float
    date: Optional[str] = None
    merchant: Optional[str] = None
    transaction_type: Optional[str] = "debit"


# ── Responses ─────────────────────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    processing_id: str
    statement_id: str
    status: str
    estimated_time_seconds: int
    message: str


class ProcessingResults(BaseModel):
    total_transactions: int = 0
    successfully_extracted: int = 0
    failed_extractions: int = 0
    categories_assigned: int = 0
    confidence_scores: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}


class ProcessingStatusResponse(BaseModel):
    statement_id: str
    processing_id: str
    status: str
    progress_percentage: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    processing_time_seconds: Optional[int] = None
    results: Optional[ProcessingResults] = None


class AlternativeCategory(BaseModel):
    category: str
    subcategory: Optional[str] = None
    confidence_score: float


class SimilarTransaction(BaseModel):
    description: str
    category: str
    similarity_score: float


class CategorizeResponse(BaseModel):
    category: str
    subcategory: Optional[str] = None
    confidence_score: float
    alternative_categories: List[AlternativeCategory] = []
    tags: List[str] = []
    similar_transactions: List[SimilarTransaction] = []


class FormatFeature(BaseModel):
    format: str
    extensions: List[str]
    max_size_mb: int
    features: List[str]


class FormatsResponse(BaseModel):
    supported_formats: List[FormatFeature]
