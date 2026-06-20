from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.sadaqah import SadaqahRecord, SADAQAH_CATEGORY_LABELS
from app.schemas.sadaqah import (
    SadaqahCreate, SadaqahUpdate, SadaqahResponse,
    SadaqahListResponse, SadaqahSummary, CategoryTotal,
)

router = APIRouter()


@router.get("/sadaqah/summary", response_model=SadaqahSummary)
def get_summary(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    today = date.today()
    records = db.query(SadaqahRecord).filter(
        SadaqahRecord.user_id == user_id,
        SadaqahRecord.deleted_at.is_(None),
    ).all()

    total_all  = sum(float(r.amount) for r in records)
    total_year = sum(float(r.amount) for r in records if r.date.year == today.year)
    total_month = sum(
        float(r.amount) for r in records
        if r.date.year == today.year and r.date.month == today.month
    )

    cat_map: dict = {}
    for r in records:
        c = r.category
        if c not in cat_map:
            cat_map[c] = {"total": 0.0, "count": 0}
        cat_map[c]["total"] += float(r.amount)
        cat_map[c]["count"] += 1

    by_category = [
        CategoryTotal(
            category=cat,
            label=SADAQAH_CATEGORY_LABELS.get(cat, cat),
            total=round(vals["total"], 2),
            count=vals["count"],
        )
        for cat, vals in cat_map.items()
    ]
    by_category.sort(key=lambda x: x.total, reverse=True)

    # Monthly trend — last 12 months
    month_map: dict = {}
    for r in records:
        key = f"{r.date.year}-{r.date.month:02d}"
        month_map[key] = month_map.get(key, 0.0) + float(r.amount)
    monthly_trend = [
        {"month": k, "total": round(v, 2)}
        for k, v in sorted(month_map.items())[-12:]
    ]

    return SadaqahSummary(
        total_all_time=round(total_all, 2),
        total_this_year=round(total_year, 2),
        total_this_month=round(total_month, 2),
        by_category=by_category,
        monthly_trend=monthly_trend,
    )


@router.get("/sadaqah", response_model=SadaqahListResponse)
def list_records(
    category: Optional[str] = Query(None),
    year:     Optional[int] = Query(None),
    user_id:  int = Depends(get_current_user_id),
    db:       Session = Depends(get_db),
):
    q = db.query(SadaqahRecord).filter(
        SadaqahRecord.user_id == user_id,
        SadaqahRecord.deleted_at.is_(None),
    )
    if category:
        q = q.filter(SadaqahRecord.category == category)
    if year:
        q = q.filter(extract("year", SadaqahRecord.date) == year)
    records = q.order_by(SadaqahRecord.date.desc()).all()
    return SadaqahListResponse(records=records, total=len(records))


@router.post("/sadaqah", response_model=SadaqahResponse, status_code=201)
def create_record(
    body: SadaqahCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = SadaqahRecord(user_id=user_id, **body.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/sadaqah/{record_id}", response_model=SadaqahResponse)
def update_record(
    record_id: int,
    body: SadaqahUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = db.query(SadaqahRecord).filter(
        SadaqahRecord.id == record_id,
        SadaqahRecord.user_id == user_id,
        SadaqahRecord.deleted_at.is_(None),
    ).first()
    if not record:
        raise HTTPException(404, "Record not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(record, k, v)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/sadaqah/{record_id}", status_code=204)
def delete_record(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    record = db.query(SadaqahRecord).filter(
        SadaqahRecord.id == record_id,
        SadaqahRecord.user_id == user_id,
        SadaqahRecord.deleted_at.is_(None),
    ).first()
    if not record:
        raise HTTPException(404, "Record not found")
    record.deleted_at = datetime.utcnow()
    db.commit()
