"""Zakat service — calculation + record management."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.zakat import ZakatRecord
from app.schemas.zakat import ZakatCalculationRequest, ZakatPaymentUpdate

logger = logging.getLogger(__name__)

_ZAKAT_RATE = Decimal("2.5")

# Approximate nisab values in USD (update periodically)
_NISAB_GOLD_GRAMS = Decimal("85")     # grams
_NISAB_SILVER_GRAMS = Decimal("595")  # grams
_GOLD_PRICE_USD_PER_GRAM = Decimal("63")    # approx
_SILVER_PRICE_USD_PER_GRAM = Decimal("0.80")

_NISAB_GOLD_USD = _NISAB_GOLD_GRAMS * _GOLD_PRICE_USD_PER_GRAM    # ~$5,355
_NISAB_SILVER_USD = _NISAB_SILVER_GRAMS * _SILVER_PRICE_USD_PER_GRAM  # ~$476

_EXCHANGE_TO_USD: Dict[str, Decimal] = {
    "USD": Decimal("1.0"),
    "PKR": Decimal("0.00357"),
    "SAR": Decimal("0.267"),
    "AED": Decimal("0.272"),
    "GBP": Decimal("1.27"),
    "EUR": Decimal("1.09"),
    "CAD": Decimal("0.74"),
    "AUD": Decimal("0.65"),
}


def get_nisab_threshold(currency: str = "USD") -> Dict[str, Any]:
    currency = currency.upper()
    rate = _EXCHANGE_TO_USD.get(currency, Decimal("1.0"))

    gold_val = _NISAB_GOLD_USD / rate
    silver_val = _NISAB_SILVER_USD / rate

    return {
        "date": date.today(),
        "currency": currency,
        "gold_nisab": {
            "grams": float(_NISAB_GOLD_GRAMS),
            "value": round(float(gold_val), 2),
            "price_per_gram_usd": float(_GOLD_PRICE_USD_PER_GRAM),
        },
        "silver_nisab": {
            "grams": float(_NISAB_SILVER_GRAMS),
            "value": round(float(silver_val), 2),
            "price_per_gram_usd": float(_SILVER_PRICE_USD_PER_GRAM),
        },
        "recommended_nisab": "silver",
        "threshold": round(float(silver_val), 2),
        "note": "Nisab values are approximate. Verify with current gold/silver prices.",
    }


def calculate(db: Session, user_id: int, data: ZakatCalculationRequest) -> ZakatRecord:
    """
    Calculate zakat and persist the record.
    Client provides nisab_threshold (from GET /zakat/nisab).
    zakatable_amount = sum(assets) - sum(liabilities)
    zakat_due = 2.5% × zakatable_amount  (if >= nisab_threshold)
    """
    total_assets = sum([
        data.cash_in_hand or Decimal("0"),
        data.bank_balance or Decimal("0"),
        data.gold_value or Decimal("0"),
        data.silver_value or Decimal("0"),
        data.investments or Decimal("0"),
        data.business_assets or Decimal("0"),
        data.receivables or Decimal("0"),
        data.other_assets or Decimal("0"),
    ])
    total_liabilities = sum([
        data.immediate_debts or Decimal("0"),
        data.other_liabilities or Decimal("0"),
    ])
    zakatable = total_assets - total_liabilities
    nisab = data.nisab_threshold
    nisab_met = zakatable >= nisab
    zakat_amount = (zakatable * _ZAKAT_RATE / 100).quantize(Decimal("0.01")) if nisab_met else Decimal("0.00")

    record = ZakatRecord(
        user_id=user_id,
        calculation_date=data.calculation_date,
        hijri_year=data.hijri_year,
        currency=data.currency.upper(),
        cash_in_hand=data.cash_in_hand,
        bank_balance=data.bank_balance,
        gold_value=data.gold_value,
        silver_value=data.silver_value,
        investments=data.investments,
        business_assets=data.business_assets,
        receivables=data.receivables,
        other_assets=data.other_assets,
        immediate_debts=data.immediate_debts,
        other_liabilities=data.other_liabilities,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        zakatable_amount=zakatable,
        nisab_threshold=nisab,
        nisab_met=nisab_met,
        zakat_rate=_ZAKAT_RATE,
        zakat_due=zakat_amount,
        payment_status="pending",
        amount_paid=Decimal("0.00"),
        notes=data.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        from app.events.producer import publish_zakat_calculated
        publish_zakat_calculated(user_id, {
            "record_id": record.id,
            "zakatable_amount": float(zakatable),
            "zakat_due": float(zakat_amount),
            "currency": record.currency,
            "nisab_met": nisab_met,
        })
    except Exception as exc:
        logger.warning("Kafka publish failed (non-fatal): %s", exc)

    return record


def list_records(
    db: Session, user_id: int,
    year: Optional[int] = None,
    paid: Optional[bool] = None,
) -> List[ZakatRecord]:
    q = db.query(ZakatRecord).filter(ZakatRecord.user_id == user_id)
    if year is not None:
        # year filter on calculation_date year
        q = q.filter(ZakatRecord.calculation_date >= date(year, 1, 1),
                     ZakatRecord.calculation_date <= date(year, 12, 31))
    if paid is not None:
        status_filter = "paid" if paid else "pending"
        q = q.filter(ZakatRecord.payment_status == status_filter)
    return q.order_by(ZakatRecord.calculation_date.desc()).all()


def get_record(db: Session, user_id: int, record_id: int) -> Optional[ZakatRecord]:
    return db.query(ZakatRecord).filter(
        ZakatRecord.id == record_id,
        ZakatRecord.user_id == user_id,
    ).first()


def update_payment(db: Session, record: ZakatRecord, data: ZakatPaymentUpdate) -> ZakatRecord:
    record.amount_paid = data.amount_paid
    record.payment_date = data.payment_date
    record.payment_status = data.payment_status
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record: ZakatRecord) -> None:
    db.delete(record)
    db.commit()
