import math
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import ActiveTimer, TimeEntry, Job


def check_overlap(db: Session, user_id: str, exclude_timer_id: str | None = None) -> ActiveTimer | None:
    q = db.query(ActiveTimer).filter(ActiveTimer.user_id == user_id)
    if exclude_timer_id:
        q = q.filter(ActiveTimer.id != exclude_timer_id)
    return q.first()


def start_timer(db: Session, user_id: str, job_id: str, notes: str | None, is_billable: bool) -> ActiveTimer:
    existing = check_overlap(db, user_id)
    if existing:
        raise ValueError(f"Timer already running for job {existing.job_id}. Stop it first.")

    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if not job:
        raise ValueError("Job not found")
    if job.status != "active":
        raise ValueError("Cannot start timer on a non-active job")

    timer = ActiveTimer(
        user_id=user_id,
        job_id=job_id,
        notes=notes,
        is_billable=is_billable,
        start_time=datetime.now(timezone.utc),
    )
    db.add(timer)
    db.commit()
    db.refresh(timer)
    return timer


def stop_timer(db: Session, user_id: str, timer_id: str, notes: str | None, rounding_rule: str) -> TimeEntry:
    timer = db.query(ActiveTimer).filter(
        ActiveTimer.id == timer_id, ActiveTimer.user_id == user_id
    ).first()
    if not timer:
        raise ValueError("Timer not found")

    end_time = datetime.now(timezone.utc)
    duration = int((end_time - timer.start_time.replace(tzinfo=timezone.utc)).total_seconds())
    if duration < 0:
        duration = 0

    rounded = apply_rounding(duration, rounding_rule)

    entry = TimeEntry(
        user_id=user_id,
        job_id=timer.job_id,
        start_time=timer.start_time,
        end_time=end_time,
        duration_seconds=duration,
        is_billable=timer.is_billable,
        notes=notes or timer.notes,
        rounding_rule=rounding_rule,
        rounded_duration_seconds=rounded,
    )
    db.add(entry)
    db.delete(timer)
    db.commit()
    db.refresh(entry)
    return entry


def apply_rounding(seconds: int, rule: str) -> int:
    if rule == "none" or not rule:
        return seconds

    minutes = seconds / 60.0

    if rule == "nearest_15":
        rounded_min = math.floor(minutes / 15 + 0.5) * 15
    elif rule == "nearest_6":
        rounded_min = math.floor(minutes / 6 + 0.5) * 6
    elif rule == "up_15":
        rounded_min = math.ceil(minutes / 15) * 15
    else:
        return seconds

    return max(int(rounded_min * 60), 0)
