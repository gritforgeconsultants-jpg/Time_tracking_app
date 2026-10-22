from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ActiveTimer, TimeEntry, Job, Customer, AuditLog
from app.schemas import (
    TimerStart, TimerStop, TimeEntryCreate, TimeEntryUpdate,
    TimeEntryOut, ActiveTimerOut,
)
from app.auth import get_current_user
from app.services.timer_service import start_timer, stop_timer, apply_rounding

router = APIRouter(prefix="/api/timers", tags=["timers"])


@router.get("/active", response_model=list[ActiveTimerOut])
def get_active_timers(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    timers = db.query(ActiveTimer).filter(ActiveTimer.user_id == user.id).all()
    now = datetime.now(timezone.utc)
    result = []
    for t in timers:
        job = db.query(Job).filter(Job.id == t.job_id).first()
        cust = db.query(Customer).filter(Customer.id == job.customer_id).first() if job else None
        start = t.start_time.replace(tzinfo=timezone.utc) if t.start_time.tzinfo is None else t.start_time
        elapsed = int((now - start).total_seconds())
        result.append(ActiveTimerOut(
            id=t.id,
            job_id=t.job_id,
            start_time=t.start_time,
            notes=t.notes,
            is_billable=t.is_billable,
            job_title=job.title if job else None,
            customer_name=cust.name if cust else None,
            elapsed_seconds=elapsed,
        ))
    return result


@router.post("/start", response_model=ActiveTimerOut)
def start(data: TimerStart, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        timer = start_timer(db, user.id, data.job_id, data.notes, data.is_billable)
    except ValueError as e:
        raise HTTPException(400, str(e))
    job = db.query(Job).filter(Job.id == timer.job_id).first()
    cust = db.query(Customer).filter(Customer.id == job.customer_id).first() if job else None
    return ActiveTimerOut(
        id=timer.id,
        job_id=timer.job_id,
        start_time=timer.start_time,
        notes=timer.notes,
        is_billable=timer.is_billable,
        job_title=job.title if job else None,
        customer_name=cust.name if cust else None,
        elapsed_seconds=0,
    )


@router.post("/stop", response_model=TimeEntryOut)
def stop(data: TimerStop, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        entry = stop_timer(db, user.id, data.timer_id, data.notes, data.rounding_rule)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return entry


@router.get("/entries", response_model=list[TimeEntryOut])
def list_entries(
    job_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(TimeEntry).filter(TimeEntry.user_id == user.id)
    if job_id:
        q = q.filter(TimeEntry.job_id == job_id)
    return q.order_by(TimeEntry.start_time.desc()).all()


@router.post("/entries", response_model=TimeEntryOut, status_code=201)
def create_manual_entry(
    data: TimeEntryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == data.job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    duration = int((data.end_time - data.start_time).total_seconds())
    if duration < 0:
        raise HTTPException(400, "End time must be after start time")

    rounded = apply_rounding(duration, data.rounding_rule)

    entry = TimeEntry(
        user_id=user.id,
        job_id=data.job_id,
        start_time=data.start_time,
        end_time=data.end_time,
        duration_seconds=duration,
        is_billable=data.is_billable,
        notes=data.notes,
        rounding_rule=data.rounding_rule,
        rounded_duration_seconds=rounded,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/entries/{eid}", response_model=TimeEntryOut)
def update_entry(
    eid: str,
    data: TimeEntryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(TimeEntry).filter(TimeEntry.id == eid, TimeEntry.user_id == user.id).first()
    if not entry:
        raise HTTPException(404, "Time entry not found")
    if entry.is_billed:
        raise HTTPException(400, "Cannot edit a billed entry")

    changes = data.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(entry, k, v)

    # Recalculate duration if times changed
    if entry.start_time and entry.end_time:
        entry.duration_seconds = int((entry.end_time - entry.start_time).total_seconds())
        entry.rounded_duration_seconds = apply_rounding(
            entry.duration_seconds, entry.rounding_rule or "none"
        )

    db.add(AuditLog(
        user_id=user.id, entity_type="time_entry", entity_id=eid,
        action="update", new_values={k: str(v) for k, v in changes.items()},
    ))
    db.commit()
    db.refresh(entry)
    return entry
