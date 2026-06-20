from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, Date
from sqlalchemy.sql import func
from app.core.database import Base

SADAQAH_CATEGORIES = [
    "sadaqah", "zakat_fitrah", "lillah", "waqf", "fidya", "kaffarah", "general_charity"
]

SADAQAH_CATEGORY_LABELS = {
    "sadaqah":        "Sadaqah (Voluntary)",
    "zakat_fitrah":   "Zakat al-Fitr",
    "lillah":         "Lillah",
    "waqf":           "Waqf (Endowment)",
    "fidya":          "Fidya",
    "kaffarah":       "Kaffarah (Expiation)",
    "general_charity":"General Charity",
}


class SadaqahRecord(Base):
    __tablename__ = "sadaqah_records"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, nullable=False, index=True)

    amount     = Column(Numeric(15, 2), nullable=False)
    currency   = Column(String(10), default="USD")
    category   = Column(String(50), nullable=False, index=True)
    recipient  = Column(String(255))       # org / person name
    date       = Column(Date, nullable=False, index=True)
    notes      = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))
