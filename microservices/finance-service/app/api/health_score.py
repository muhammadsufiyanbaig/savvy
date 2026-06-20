from __future__ import annotations

from datetime import date, datetime
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.asset import Asset
from app.models.budget import Budget
from app.models.liability import Liability
from app.models.savings import SavingsGoal
from app.models.cash_savings import CashSavings
from app.models.spending_limit import SpendingLimit
from app.models.zakat import ZakatRecord
from app.models.sadaqah import SadaqahRecord
from app.models.expense import Expense

router = APIRouter()


class ScoreComponent(BaseModel):
    key:         str
    name:        str
    score:       int
    max_score:   int
    pct:         float
    status:      str   # good / warning / poor
    tip:         str


class HealthScoreResponse(BaseModel):
    total_score:    int
    grade:          str   # A / B / C / D / F
    components:     List[ScoreComponent]
    summary:        str
    calculated_at:  datetime


def _grade(score: int) -> str:
    if score >= 85: return "A"
    if score >= 70: return "B"
    if score >= 55: return "C"
    if score >= 40: return "D"
    return "F"


def _status(pct: float) -> str:
    if pct >= 0.75: return "good"
    if pct >= 0.40: return "warning"
    return "poor"


@router.get("/financial-health/score", response_model=HealthScoreResponse)
def get_health_score(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    today  = date.today()
    year   = today.year
    month  = today.month
    components: List[ScoreComponent] = []

    # ── 1. Savings Rate (25 pts) ──────────────────────────────────────────────
    # Proxy: savings goal deposits this month vs total expenses this month
    from sqlalchemy import extract
    monthly_expenses = db.query(Expense).filter(
        Expense.user_id == user_id,
        Expense.deleted_at.is_(None),
        extract("year", Expense.date) == year,
        extract("month", Expense.date) == month,
    ).all()
    total_exp = sum(float(e.amount) for e in monthly_expenses) or 1.0

    cash_savings = db.query(CashSavings).filter(
        CashSavings.user_id == user_id,
        CashSavings.deleted_at.is_(None),
    ).all()
    total_cash_saved = sum(float(c.amount) for c in cash_savings)

    savings_ratio = min(total_cash_saved / (total_exp * 6), 1.0)  # 6-month coverage = perfect
    savings_score = round(savings_ratio * 25)
    components.append(ScoreComponent(
        key="savings_rate",
        name="Savings Rate",
        score=savings_score, max_score=25,
        pct=savings_ratio,
        status=_status(savings_ratio),
        tip="Aim for at least 3–6 months of expenses in savings."
            if savings_ratio < 0.75 else "Great! You have solid emergency savings.",
    ))

    # ── 2. Budget Adherence (20 pts) ──────────────────────────────────────────
    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.deleted_at.is_(None),
        Budget.is_active == True,
    ).all()
    if budgets:
        period = f"{year}-{month:02d}"
        on_track = sum(
            1 for b in budgets
            if float(b.spent_amount or 0) <= float(b.limit_amount)
        )
        budget_ratio = on_track / len(budgets)
    else:
        budget_ratio = 0.5  # no budgets = neutral
    budget_score = round(budget_ratio * 20)
    components.append(ScoreComponent(
        key="budget_adherence",
        name="Budget Adherence",
        score=budget_score, max_score=20,
        pct=budget_ratio,
        status=_status(budget_ratio),
        tip="Set budgets for all major categories and stay within them."
            if budget_ratio < 0.75 else "You're staying within your budgets — keep it up!",
    ))

    # ── 3. Debt Ratio (20 pts) ────────────────────────────────────────────────
    liabilities = db.query(Liability).filter(
        Liability.user_id == user_id,
        Liability.deleted_at.is_(None),
        Liability.is_active == True,
    ).all()
    assets = db.query(Asset).filter(
        Asset.user_id == user_id,
        Asset.deleted_at.is_(None),
        Asset.is_active == True,
    ).all()
    total_assets = sum(float(a.current_price_per_unit) * float(a.quantity) for a in assets) or 1.0
    total_debt   = sum(float(l.amount_owed) for l in liabilities)
    riba_debt    = sum(float(l.amount_owed) for l in liabilities if l.is_interest_bearing)

    debt_ratio   = total_debt / total_assets if total_assets > 0 else 1.0
    debt_score_raw = max(1.0 - debt_ratio, 0.0)
    # Penalise riba debt extra
    riba_penalty = min(riba_debt / total_assets, 0.3) if total_assets > 0 else 0.0
    final_debt_ratio = min(max(debt_score_raw - riba_penalty, 0.0), 1.0)
    debt_score = round(final_debt_ratio * 20)

    debt_tip = "You have interest-bearing (riba) debt — consider paying it off first." \
        if riba_debt > 0 else (
        "Work on reducing your total debt." if debt_ratio > 0.5
        else "Excellent! Low debt relative to assets."
    )
    components.append(ScoreComponent(
        key="debt_ratio",
        name="Debt Ratio",
        score=debt_score, max_score=20,
        pct=final_debt_ratio,
        status=_status(final_debt_ratio),
        tip=debt_tip,
    ))

    # ── 4. Zakat Compliance (15 pts) ──────────────────────────────────────────
    zakat_paid_this_year = db.query(ZakatRecord).filter(
        ZakatRecord.user_id == user_id,
        ZakatRecord.deleted_at.is_(None),
        extract("year", ZakatRecord.calculated_at) == year,
        ZakatRecord.is_paid == True,
    ).count()
    zakat_due_this_year = db.query(ZakatRecord).filter(
        ZakatRecord.user_id == user_id,
        ZakatRecord.deleted_at.is_(None),
        extract("year", ZakatRecord.calculated_at) == year,
    ).count()

    if zakat_due_this_year == 0:
        zakat_ratio = 1.0   # nothing calculated = not applicable
    else:
        zakat_ratio = zakat_paid_this_year / zakat_due_this_year

    zakat_score = round(zakat_ratio * 15)
    components.append(ScoreComponent(
        key="zakat_compliance",
        name="Zakat Compliance",
        score=zakat_score, max_score=15,
        pct=zakat_ratio,
        status=_status(zakat_ratio),
        tip="You have unpaid zakat — fulfil your obligation."
            if zakat_ratio < 1.0 and zakat_due_this_year > 0
            else "Zakat is up to date. JazakAllah khair!",
    ))

    # ── 5. Sadaqah / Charity (10 pts) ─────────────────────────────────────────
    sadaqah_this_year = db.query(SadaqahRecord).filter(
        SadaqahRecord.user_id == user_id,
        SadaqahRecord.deleted_at.is_(None),
        extract("year", SadaqahRecord.date) == year,
    ).all()
    sadaqah_total = sum(float(r.amount) for r in sadaqah_this_year)
    # Score: giving ≥ 2.5% of annual expenses = perfect
    annual_exp = total_exp * 12
    sadaqah_ratio = min(sadaqah_total / (annual_exp * 0.025), 1.0) if annual_exp > 0 else 0.0
    sadaqah_score = round(sadaqah_ratio * 10)
    components.append(ScoreComponent(
        key="charitable_giving",
        name="Charitable Giving",
        score=sadaqah_score, max_score=10,
        pct=sadaqah_ratio,
        status=_status(sadaqah_ratio),
        tip="Regular sadaqah strengthens barakah in wealth — try giving at least 2.5% of expenses."
            if sadaqah_ratio < 0.75 else "MashaAllah! Consistent in giving.",
    ))

    # ── 6. Goal Progress (10 pts) ─────────────────────────────────────────────
    goals = db.query(SavingsGoal).filter(
        SavingsGoal.user_id == user_id,
        SavingsGoal.deleted_at.is_(None),
        SavingsGoal.is_active == True,
    ).all()
    if goals:
        avg_progress = sum(
            min(float(g.current_amount) / float(g.target_amount), 1.0)
            for g in goals if float(g.target_amount) > 0
        ) / len(goals)
    else:
        avg_progress = 0.5
    goal_score = round(avg_progress * 10)
    components.append(ScoreComponent(
        key="goal_progress",
        name="Goal Progress",
        score=goal_score, max_score=10,
        pct=avg_progress,
        status=_status(avg_progress),
        tip="Set savings goals and make regular deposits to stay on track."
            if avg_progress < 0.75 else "Great progress on your savings goals!",
    ))

    overall = sum(c.score for c in components)
    grade   = _grade(overall)

    summaries = {
        "A": "Excellent financial health. You're managing money in a disciplined, Islamic-compliant way.",
        "B": "Good financial health. A few areas to tighten up.",
        "C": "Fair. Several areas need attention — focus on the lowest-scoring components.",
        "D": "Below average. Prioritise debt reduction, budgeting, and savings.",
        "F": "Critical. Take immediate action on your finances.",
    }

    return HealthScoreResponse(
        total_score=overall,
        grade=grade,
        components=components,
        summary=summaries[grade],
        calculated_at=datetime.utcnow(),
    )
