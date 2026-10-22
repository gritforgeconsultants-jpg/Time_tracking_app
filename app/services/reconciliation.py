from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import AIAPIUsage, ReconciliationRecord


def reconcile_provider(
    db: Session,
    user_id: str,
    provider: str,
    period_start: datetime,
    period_end: datetime,
    actual_total: Decimal,
    notes: str | None = None,
) -> ReconciliationRecord:
    expected_row = db.query(
        func.coalesce(func.sum(AIAPIUsage.calculated_cost), 0)
    ).filter(
        AIAPIUsage.user_id == user_id,
        AIAPIUsage.provider == provider,
        AIAPIUsage.timestamp >= period_start,
        AIAPIUsage.timestamp <= period_end,
    ).scalar()

    expected = Decimal(str(expected_row))
    discrepancy = actual_total - expected

    abs_disc = abs(discrepancy)
    status = "resolved" if abs_disc < Decimal("0.01") else "flagged"

    # Find records missing from our logs vs billing
    usage_count = db.query(AIAPIUsage).filter(
        AIAPIUsage.user_id == user_id,
        AIAPIUsage.provider == provider,
        AIAPIUsage.timestamp >= period_start,
        AIAPIUsage.timestamp <= period_end,
    ).count()

    details = {
        "logged_requests": usage_count,
        "expected_total": str(expected),
        "actual_total": str(actual_total),
        "discrepancy": str(discrepancy),
    }

    record = ReconciliationRecord(
        user_id=user_id,
        provider=provider,
        period_start=period_start,
        period_end=period_end,
        expected_total=expected,
        actual_total=actual_total,
        discrepancy=discrepancy,
        status=status,
        details=details,
        notes=notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
