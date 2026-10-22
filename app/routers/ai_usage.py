from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, AIAPIUsage, AIPricing, Job
from app.schemas import AIUsageCreate, AIUsageOut, PricingCreate, PricingOut
from app.auth import get_current_user
from app.services.ai_tracking import log_usage

router = APIRouter(prefix="/api/ai", tags=["ai_usage"])


@router.get("/usage", response_model=list[AIUsageOut])
def list_usage(
    job_id: str | None = None,
    provider: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(AIAPIUsage).filter(AIAPIUsage.user_id == user.id)
    if job_id:
        q = q.filter(AIAPIUsage.job_id == job_id)
    if provider:
        q = q.filter(AIAPIUsage.provider == provider)
    return q.order_by(AIAPIUsage.timestamp.desc()).limit(200).all()


@router.post("/usage", response_model=AIUsageOut, status_code=201)
def record_usage(data: AIUsageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == data.job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    try:
        record = log_usage(
            db=db,
            user_id=user.id,
            job_id=data.job_id,
            provider=data.provider,
            model=data.model,
            input_tokens=data.input_tokens,
            output_tokens=data.output_tokens,
            cached_tokens=data.cached_tokens,
            provider_request_id=data.provider_request_id,
            other_units=data.other_units,
            duration_ms=data.duration_ms,
            status=data.status,
            cost_override=data.calculated_cost,
            timestamp=data.timestamp,
        )
    except ValueError as e:
        raise HTTPException(409, str(e))
    return record


@router.get("/pricing", response_model=list[PricingOut])
def list_pricing(
    provider: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(AIPricing)
    if provider:
        q = q.filter(AIPricing.provider == provider)
    return q.order_by(AIPricing.provider, AIPricing.model, AIPricing.effective_date.desc()).all()


@router.post("/pricing", response_model=PricingOut, status_code=201)
def create_pricing(data: PricingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = AIPricing(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/providers")
def list_providers(user: User = Depends(get_current_user)):
    from app.config import settings
    return {
        "providers": [
            {"name": "openai", "display": "OpenAI / ChatGPT", "api_connected": bool(settings.openai_api_key)},
            {"name": "anthropic", "display": "Claude / Anthropic", "api_connected": bool(settings.anthropic_api_key)},
            {"name": "google", "display": "Gemini / Google", "api_connected": bool(settings.google_ai_api_key)},
            {"name": "xai", "display": "Grok / xAI", "api_connected": bool(settings.xai_api_key)},
        ]
    }
