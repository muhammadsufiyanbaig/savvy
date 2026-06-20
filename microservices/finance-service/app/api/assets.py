from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.asset import Asset, ASSET_CATEGORIES, ASSET_CATEGORY_LABELS
from app.schemas.asset import (
    AssetCreate, AssetUpdate, AssetResponse,
    AssetListResponse, AssetAnalytics,
    CategoryBreakdown, YearlySnapshot,
)

router = APIRouter()


def _enrich(asset: Asset) -> AssetResponse:
    """Attach computed gain/loss fields."""
    purchase_value = Decimal(str(asset.purchase_price_per_unit)) * Decimal(str(asset.quantity))
    current_value  = Decimal(str(asset.current_price_per_unit))  * Decimal(str(asset.quantity))
    gain_loss      = current_value - purchase_value
    gain_loss_pct  = float(gain_loss / purchase_value * 100) if purchase_value else 0.0

    resp = AssetResponse.model_validate(asset)
    resp.purchase_value = purchase_value
    resp.current_value  = current_value
    resp.gain_loss      = gain_loss
    resp.gain_loss_pct  = round(gain_loss_pct, 2)
    return resp


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/assets", response_model=AssetListResponse)
def list_assets(
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    q = db.query(Asset).filter(
        Asset.user_id == user_id,
        Asset.deleted_at.is_(None),
    )
    if category:
        q = q.filter(Asset.category == category)
    if is_active is not None:
        q = q.filter(Asset.is_active == is_active)
    assets = q.order_by(Asset.category, Asset.name).all()
    return AssetListResponse(assets=[_enrich(a) for a in assets], total=len(assets))


@router.post("/assets", response_model=AssetResponse, status_code=201)
def create_asset(
    body: AssetCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    asset = Asset(user_id=user_id, **body.model_dump())
    asset.last_price_updated = datetime.utcnow()
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _enrich(asset)


# ── Analytics (must be before /{asset_id} to avoid route shadowing) ───────────

@router.get("/assets/analytics/summary", response_model=AssetAnalytics)
def get_analytics(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    assets = db.query(Asset).filter(
        Asset.user_id == user_id,
        Asset.deleted_at.is_(None),
    ).all()

    if not assets:
        return AssetAnalytics(
            total_current_value=0, total_purchase_value=0,
            total_gain_loss=0, total_gain_loss_pct=0,
            total_assets=0, active_assets=0,
            by_category=[], yearly_growth=[],
        )

    enriched = [_enrich(a) for a in assets]

    total_current  = sum(float(e.current_value)  for e in enriched)
    total_purchase = sum(float(e.purchase_value) for e in enriched)
    total_gl       = total_current - total_purchase
    total_gl_pct   = round(total_gl / total_purchase * 100, 2) if total_purchase else 0.0

    # ── By category ──────────────────────────────────────────────────────────
    cat_map: dict = {}
    for e in enriched:
        c = e.category
        if c not in cat_map:
            cat_map[c] = {"count": 0, "current": 0.0, "purchase": 0.0}
        cat_map[c]["count"]    += 1
        cat_map[c]["current"]  += float(e.current_value)
        cat_map[c]["purchase"] += float(e.purchase_value)

    by_category = []
    for cat, vals in cat_map.items():
        gl = vals["current"] - vals["purchase"]
        gl_pct = round(gl / vals["purchase"] * 100, 2) if vals["purchase"] else 0.0
        pct_portfolio = round(vals["current"] / total_current * 100, 2) if total_current else 0.0
        by_category.append(CategoryBreakdown(
            category=cat,
            label=ASSET_CATEGORY_LABELS.get(cat, cat),
            count=vals["count"],
            current_value=round(vals["current"], 2),
            purchase_value=round(vals["purchase"], 2),
            gain_loss=round(gl, 2),
            gain_loss_pct=gl_pct,
            percentage_of_portfolio=pct_portfolio,
        ))
    by_category.sort(key=lambda x: x.current_value, reverse=True)

    # ── Yearly growth ─────────────────────────────────────────────────────────
    # Group assets by purchase year and compute cumulative portfolio value per year
    current_year = date.today().year
    years_seen = sorted({a.purchase_date.year for a in assets})
    if not years_seen:
        years_seen = [current_year]
    first_year = years_seen[0]
    year_range = list(range(first_year, current_year + 1))

    yearly_growth = []
    for yr in year_range:
        # Assets purchased up to and including this year
        yr_assets = [e for e in enriched if assets[enriched.index(e)].purchase_date.year <= yr]
        if not yr_assets:
            continue
        yr_purchase = sum(float(e.purchase_value) for e in yr_assets)
        # For past years use purchase_value as proxy; current year uses live price
        yr_current  = sum(float(e.current_value) for e in yr_assets) if yr == current_year \
                      else yr_purchase  # historical: treat as par (no time-series data yet)
        yr_gl       = yr_current - yr_purchase
        yr_gl_pct   = round(yr_gl / yr_purchase * 100, 2) if yr_purchase else 0.0
        yearly_growth.append(YearlySnapshot(
            year=yr,
            total_value=round(yr_current, 2),
            total_invested=round(yr_purchase, 2),
            gain_loss=round(yr_gl, 2),
            gain_loss_pct=yr_gl_pct,
        ))

    # ── Top/worst performers ──────────────────────────────────────────────────
    active_enriched = [e for e in enriched if e.is_active]
    top     = max(active_enriched, key=lambda e: e.gain_loss_pct, default=None)
    worst   = min(active_enriched, key=lambda e: e.gain_loss_pct, default=None)

    return AssetAnalytics(
        total_current_value=round(total_current, 2),
        total_purchase_value=round(total_purchase, 2),
        total_gain_loss=round(total_gl, 2),
        total_gain_loss_pct=total_gl_pct,
        total_assets=len(enriched),
        active_assets=sum(1 for e in enriched if e.is_active),
        by_category=by_category,
        yearly_growth=yearly_growth,
        top_performer={"id": top.id, "name": top.name, "gain_loss_pct": top.gain_loss_pct} if top else None,
        worst_performer={"id": worst.id, "name": worst.name, "gain_loss_pct": worst.gain_loss_pct} if worst else None,
    )


# ── CRUD by ID ────────────────────────────────────────────────────────────────

@router.get("/assets/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == user_id,
        Asset.deleted_at.is_(None),
    ).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    return _enrich(asset)


@router.put("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    body: AssetUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == user_id,
        Asset.deleted_at.is_(None),
    ).first()
    if not asset:
        raise HTTPException(404, "Asset not found")

    updates = body.model_dump(exclude_none=True)
    if "current_price_per_unit" in updates:
        asset.last_price_updated = datetime.utcnow()
    for k, v in updates.items():
        setattr(asset, k, v)

    db.commit()
    db.refresh(asset)
    return _enrich(asset)


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(
    asset_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == user_id,
        Asset.deleted_at.is_(None),
    ).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    asset.deleted_at = datetime.utcnow()
    db.commit()
