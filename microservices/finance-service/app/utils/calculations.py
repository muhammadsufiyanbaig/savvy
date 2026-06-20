"""
Pure financial calculation helpers — no DB, no I/O.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


def calc_progress(current: Decimal, target: Decimal) -> Decimal:
    """Return progress as 0–100 Decimal(5,2)."""
    if target <= 0:
        return Decimal("0.00")
    pct = (current / target * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return min(pct, Decimal("100.00"))


def calc_zakat(zakatable: Decimal, nisab: Decimal, rate: Decimal = Decimal("2.5")) -> Decimal:
    """Return zakat due. 0 if zakatable < nisab."""
    if zakatable < nisab:
        return Decimal("0.00")
    return (zakatable * rate / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calc_next_occurrence(current_date: date, pattern: str) -> date:
    """Return the next occurrence date for a recurring expense."""
    if pattern == "daily":
        return current_date + timedelta(days=1)
    if pattern == "weekly":
        return current_date + timedelta(weeks=1)
    if pattern == "monthly":
        month = current_date.month + 1
        year = current_date.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        try:
            return current_date.replace(year=year, month=month)
        except ValueError:
            # e.g. Jan 31 → Feb 28
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            return current_date.replace(year=year, month=month, day=last_day)
    if pattern == "yearly":
        try:
            return current_date.replace(year=current_date.year + 1)
        except ValueError:
            return current_date.replace(year=current_date.year + 1, day=28)
    return current_date + timedelta(days=30)


def days_between(start: date, end: date) -> int:
    return max(0, (end - start).days)


def get_current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def get_current_month_start() -> date:
    today = date.today()
    return today.replace(day=1)


def pct(part: float, total: float, decimals: int = 1) -> float:
    if total == 0:
        return 0.0
    return round(part / total * 100, decimals)
