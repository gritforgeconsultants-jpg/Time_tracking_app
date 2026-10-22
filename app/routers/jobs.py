from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Job, Customer, AuditLog
from app.schemas import JobCreate, JobUpdate, JobOut, JobCostSummary
from app.auth import get_current_user
from app.services.cost_calculator import calculate_job_cost

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(
    status: str | None = None,
    customer_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Job).filter(Job.user_id == user.id)
    if status:
        q = q.filter(Job.status == status)
    if customer_id:
        q = q.filter(Job.customer_id == customer_id)
    return q.order_by(Job.created_at.desc()).all()


@router.post("", response_model=JobOut, status_code=201)
def create_job(data: JobCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == data.customer_id, Customer.user_id == user.id).first()
    if not cust:
        raise HTTPException(404, "Customer not found")

    hourly = data.hourly_rate if data.hourly_rate is not None else cust.default_hourly_rate
    internal = data.internal_cost_rate if data.internal_cost_rate is not None else cust.default_internal_cost_rate

    j = Job(
        user_id=user.id,
        customer_id=data.customer_id,
        title=data.title,
        description=data.description,
        job_type=data.job_type,
        hourly_rate=hourly,
        internal_cost_rate=internal,
        fixed_price=data.fixed_price,
        budget=data.budget,
        markup_percent=data.markup_percent,
        billing_notes=data.billing_notes,
    )
    db.add(j)
    db.flush()
    db.add(AuditLog(user_id=user.id, entity_type="job", entity_id=j.id, action="create", new_values=data.model_dump(mode="json")))
    db.commit()
    db.refresh(j)
    return j


@router.get("/{jid}", response_model=JobOut)
def get_job(jid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    j = db.query(Job).filter(Job.id == jid, Job.user_id == user.id).first()
    if not j:
        raise HTTPException(404, "Job not found")
    return j


@router.patch("/{jid}", response_model=JobOut)
def update_job(jid: str, data: JobUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    j = db.query(Job).filter(Job.id == jid, Job.user_id == user.id).first()
    if not j:
        raise HTTPException(404, "Job not found")
    changes = data.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(j, k, v)
    db.add(AuditLog(user_id=user.id, entity_type="job", entity_id=j.id, action="update", new_values={k: str(v) for k, v in changes.items()}))
    db.commit()
    db.refresh(j)
    return j


@router.get("/{jid}/cost", response_model=JobCostSummary)
def job_cost(jid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return calculate_job_cost(db, jid, user.id)
