from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.asset import Asset, ASSET_CATEGORY_LABELS
from app.models.liability import Liability, LIABILITY_CATEGORY_LABELS
from app.schemas.liability import (
    LiabilityCreate, LiabilityUpdate, LiabilityResponse,
    LiabilityListResponse, NetWorthResponse,
)

router = APIRouter()


@router.get("/liabilities/net-worth", response_model=NetWorthResponse)
def get_net_worth(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    assets = db.query(Asset).filter(
        Asset.user_id == user_id,
        Asset.deleted_at.is_(None),
        Asset.is_active == True,
    ).all()

    liabilities = db.query(Liability).filter(
        Liability.user_id == user_id,
        Liability.deleted_at.is_(None),
        Liability.is_active == True,
    ).all()

    total_assets = sum(
        float(a.current_price_per_unit) * float(a.quantity) for a in assets
    )

    total_liabilities = sum(float(l.amount_owed) for l in liabilities)
    net_worth = total_assets - total_liabilities

    # Assets by category
    asset_cat: dict = {}
    for a in assets:
        val = float(a.current_price_per_unit) * float(a.quantity)
        if a.category not in asset_cat:
            asset_cat[a.category] = 0.0
        asset_cat[a.category] += val

    assets_by_cat = [
        {"category": c, "label": ASSET_CATEGORY_LABELS.get(c, c), "total": round(v, 2)}
        for c, v in sorted(asset_cat.items(), key=lambda x: x[1], reverse=True)
    ]

    # Liabilities by category
    liab_cat: dict = {}
    for l in liabilities:
        if l.category not in liab_cat:
            liab_cat[l.category] = 0.0
        liab_cat[l.category] += float(l.amount_owed)

    liab_by_cat = [
        {"category": c, "label": LIABILITY_CATEGORY_LABELS.get(c, c), "total": round(v, 2)}
        for c, v in sorted(liab_cat.items(), key=lambda x: x[1], reverse=True)
    ]

    riba_total  = sum(float(l.amount_owed) for l in liabilities if l.is_interest_bearing)
    halal_total = sum(float(l.amount_owed) for l in liabilities if not l.is_interest_bearing)

    return NetWorthResponse(
        total_assets=round(total_assets, 2),
        total_liabilities=round(total_liabilities, 2),
        net_worth=round(net_worth, 2),
        assets_by_category=assets_by_cat,
        liabilities_by_category=liab_by_cat,
        riba_debt_total=round(riba_total, 2),
        halal_debt_total=round(halal_total, 2),
    )


@router.get("/liabilities", response_model=LiabilityListResponse)
def list_liabilities(
    is_active:          Optional[bool] = Query(None),
    is_interest_bearing: Optional[bool] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    q = db.query(Liability).filter(
        Liability.user_id == user_id,
        Liability.deleted_at.is_(None),
    )
    if is_active is not None:
        q = q.filter(Liability.is_active == is_active)
    if is_interest_bearing is not None:
        q = q.filter(Liability.is_interest_bearing == is_interest_bearing)
    items = q.order_by(Liability.amount_owed.desc()).all()
    return LiabilityListResponse(liabilities=items, total=len(items))


@router.post("/liabilities", response_model=LiabilityResponse, status_code=201)
def create_liability(
    body: LiabilityCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = Liability(user_id=user_id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/liabilities/{liability_id}", response_model=LiabilityResponse)
def update_liability(
    liability_id: int,
    body: LiabilityUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = db.query(Liability).filter(
        Liability.id == liability_id,
        Liability.user_id == user_id,
        Liability.deleted_at.is_(None),
    ).first()
    if not item:
        raise HTTPException(404, "Liability not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/liabilities/{liability_id}", status_code=204)
def delete_liability(
    liability_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = db.query(Liability).filter(
        Liability.id == liability_id,
        Liability.user_id == user_id,
        Liability.deleted_at.is_(None),
    ).first()
    if not item:
        raise HTTPException(404, "Liability not found")
    item.deleted_at = datetime.utcnow()
    db.commit()
