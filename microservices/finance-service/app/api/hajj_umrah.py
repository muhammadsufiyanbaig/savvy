from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.hajj_umrah import HajjUmrahPlan, HajjUmrahDeposit
from app.schemas.hajj_umrah import (
    HajjUmrahPlanCreate, HajjUmrahPlanUpdate, HajjUmrahPlanResponse,
    HajjUmrahListResponse, DepositCreate, DepositResponse,
)

router = APIRouter()


def _enrich(plan: HajjUmrahPlan) -> HajjUmrahPlanResponse:
    estimated  = Decimal(str(plan.estimated_cost))
    current    = Decimal(str(plan.current_amount))
    remaining  = max(estimated - current, Decimal(0))
    progress   = float(current / estimated * 100) if estimated else 0.0

    today = date.today()
    target_date = date(plan.target_year, 1, 1)
    months_remaining = max(
        (target_date.year - today.year) * 12 + (target_date.month - today.month), 0
    )
    monthly_target = remaining / months_remaining if months_remaining > 0 else remaining

    resp = HajjUmrahPlanResponse.model_validate(plan)
    resp.progress_pct     = round(progress, 2)
    resp.remaining_amount = round(remaining, 2)
    resp.months_remaining = months_remaining
    resp.monthly_target   = round(monthly_target, 2)
    return resp


@router.get("/hajj-umrah", response_model=HajjUmrahListResponse)
def list_plans(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    plans = db.query(HajjUmrahPlan).filter(
        HajjUmrahPlan.user_id == user_id,
        HajjUmrahPlan.deleted_at.is_(None),
    ).order_by(HajjUmrahPlan.target_year).all()
    return HajjUmrahListResponse(plans=[_enrich(p) for p in plans], total=len(plans))


@router.post("/hajj-umrah", response_model=HajjUmrahPlanResponse, status_code=201)
def create_plan(
    body: HajjUmrahPlanCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    plan = HajjUmrahPlan(user_id=user_id, **body.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _enrich(plan)


@router.put("/hajj-umrah/{plan_id}", response_model=HajjUmrahPlanResponse)
def update_plan(
    plan_id: int,
    body: HajjUmrahPlanUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    plan = db.query(HajjUmrahPlan).filter(
        HajjUmrahPlan.id == plan_id,
        HajjUmrahPlan.user_id == user_id,
        HajjUmrahPlan.deleted_at.is_(None),
    ).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(plan, k, v)
    db.commit()
    db.refresh(plan)
    return _enrich(plan)


@router.delete("/hajj-umrah/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    plan = db.query(HajjUmrahPlan).filter(
        HajjUmrahPlan.id == plan_id,
        HajjUmrahPlan.user_id == user_id,
        HajjUmrahPlan.deleted_at.is_(None),
    ).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    plan.deleted_at = datetime.utcnow()
    db.commit()


@router.post("/hajj-umrah/{plan_id}/deposit", response_model=HajjUmrahPlanResponse)
def add_deposit(
    plan_id: int,
    body: DepositCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    plan = db.query(HajjUmrahPlan).filter(
        HajjUmrahPlan.id == plan_id,
        HajjUmrahPlan.user_id == user_id,
        HajjUmrahPlan.deleted_at.is_(None),
    ).first()
    if not plan:
        raise HTTPException(404, "Plan not found")

    deposit = HajjUmrahDeposit(
        plan_id=plan_id,
        user_id=user_id,
        amount=body.amount,
        note=body.note,
        date=body.date,
    )
    db.add(deposit)
    plan.current_amount = Decimal(str(plan.current_amount)) + Decimal(str(body.amount))
    db.commit()
    db.refresh(plan)
    return _enrich(plan)


@router.get("/hajj-umrah/{plan_id}/deposits")
def list_deposits(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    plan = db.query(HajjUmrahPlan).filter(
        HajjUmrahPlan.id == plan_id,
        HajjUmrahPlan.user_id == user_id,
    ).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    deposits = db.query(HajjUmrahDeposit).filter(
        HajjUmrahDeposit.plan_id == plan_id,
    ).order_by(HajjUmrahDeposit.date.desc()).all()
    items = [DepositResponse.model_validate(d) for d in deposits]
    return {"deposits": items, "total": len(items)}
