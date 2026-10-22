from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import AIAPIUsage, AIPricing


def lookup_price(db: Session, provider: str, model: str, timestamp: datetime) -> AIPricing | None:
    return db.query(AIPricing).filter(
        AIPricing.provider == provider,
        AIPricing.model == model,
        AIPricing.effective_date <= timestamp,
        (AIPricing.end_date.is_(None)) | (AIPricing.end_date >= timestamp),
    ).order_by(AIPricing.effective_date.desc()).first()


def calculate_cost(
    pricing: AIPricing | None,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> tuple[Decimal, bool]:
    if pricing is None:
        return Decimal("0"), True

    million = Decimal("1000000")
    input_cost = Decimal(str(input_tokens)) * Decimal(str(pricing.input_price_per_million)) / million
    output_cost = Decimal(str(output_tokens)) * Decimal(str(pricing.output_price_per_million)) / million

    cached_cost = Decimal("0")
    if cached_tokens and pricing.cached_input_price_per_million is not None:
        cached_cost = Decimal(str(cached_tokens)) * Decimal(str(pricing.cached_input_price_per_million)) / million

    return input_cost + output_cost + cached_cost, True  # still estimated until reconciled


def check_duplicate(db: Session, provider: str, provider_request_id: str | None) -> bool:
    if not provider_request_id:
        return False
    return db.query(AIAPIUsage).filter(
        AIAPIUsage.provider == provider,
        AIAPIUsage.provider_request_id == provider_request_id,
    ).first() is not None


def log_usage(
    db: Session,
    user_id: str,
    job_id: str,
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    provider_request_id: str | None = None,
    other_units: dict | None = None,
    duration_ms: int | None = None,
    status: str = "success",
    cost_override: Decimal | None = None,
    timestamp: datetime | None = None,
) -> AIAPIUsage:
    if check_duplicate(db, provider, provider_request_id):
        raise ValueError(f"Duplicate request: {provider}/{provider_request_id}")

    ts = timestamp or datetime.now(timezone.utc)

    if cost_override is not None:
        cost = cost_override
        is_estimated = False
    else:
        pricing = lookup_price(db, provider, model, ts)
        cost, is_estimated = calculate_cost(pricing, input_tokens, output_tokens, cached_tokens)

    # Failed requests may still incur cost for input tokens processed
    if status == "error" and cost_override is None:
        pricing = lookup_price(db, provider, model, ts)
        if pricing:
            million = Decimal("1000000")
            cost = Decimal(str(input_tokens)) * Decimal(str(pricing.input_price_per_million)) / million
            is_estimated = True

    record = AIAPIUsage(
        user_id=user_id,
        job_id=job_id,
        provider=provider,
        model=model,
        provider_request_id=provider_request_id,
        timestamp=ts,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        other_units=other_units,
        duration_ms=duration_ms,
        status=status,
        calculated_cost=cost,
        cost_is_estimated=is_estimated,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
