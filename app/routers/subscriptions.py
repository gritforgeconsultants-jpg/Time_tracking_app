from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, AISubscription, SubscriptionAllocation, Job
from app.schemas import (
    SubscriptionCreate, SubscriptionUpdate, SubscriptionOut,
    AllocationCreate, AllocationOut,
)
from app.auth import get_current_user

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[SubscriptionOut])
def list_subscriptions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(AISubscription).filter(AISubscription.user_id == user.id).all()


@router.post("", response_model=SubscriptionOut, status_code=201)
def create_subscription(data: SubscriptionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = AISubscription(user_id=user.id, **data.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.patch("/{sid}", response_model=SubscriptionOut)
def update_subscription(sid: str, data: SubscriptionUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(AISubscription).filter(AISubscription.id == sid, AISubscription.user_id == user.id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(sub, k, v)
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/allocations", response_model=list[AllocationOut])
def list_allocations(
    subscription_id: str | None = None,
    job_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(SubscriptionAllocation).join(AISubscription).filter(AISubscription.user_id == user.id)
    if subscription_id:
        q = q.filter(SubscriptionAllocation.subscription_id == subscription_id)
    if job_id:
        q = q.filter(SubscriptionAllocation.job_id == job_id)
    return q.all()


@router.post("/allocations", response_model=AllocationOut, status_code=201)
def create_allocation(data: AllocationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(AISubscription).filter(AISubscription.id == data.subscription_id, AISubscription.user_id == user.id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")

    job = db.query(Job).filter(Job.id == data.job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    # Check allocation limit: total for this subscription+period cannot exceed 100%
    existing_pct = db.query(
        func.coalesce(func.sum(SubscriptionAllocation.allocation_percentage), 0)
    ).filter(
        SubscriptionAllocation.subscription_id == data.subscription_id,
        SubscriptionAllocation.period_start == data.period_start,
        SubscriptionAllocation.period_end == data.period_end,
    ).scalar()

    total_after = Decimal(str(existing_pct)) + data.allocation_percentage
    if total_after > Decimal("100"):
        raise HTTPException(
            400,
            f"Total allocation would be {total_after}%. Cannot exceed 100% of subscription cost. "
            f"Currently allocated: {existing_pct}%",
        )

    allocated_amount = sub.monthly_cost * data.allocation_percentage / Decimal("100")

    alloc = SubscriptionAllocation(
        subscription_id=data.subscription_id,
        job_id=data.job_id,
        period_start=data.period_start,
        period_end=data.period_end,
        allocation_method=data.allocation_method,
        allocation_percentage=data.allocation_percentage,
        allocated_amount=allocated_amount.quantize(Decimal("0.01")),
        notes=data.notes,
    )
    db.add(alloc)
    db.commit()
    db.refresh(alloc)
    return alloc
