from pydantic import BaseModel
from typing import Any, Dict, Optional


class MessageResponse(BaseModel):
    message: str
    detail: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    size: int
