from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ReconciliationRecord
from app.schemas import ReconciliationCreate, ReconciliationOut
from app.auth import get_current_user
from app.services.reconciliation import reconcile_provider

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])


@router.get("", response_model=list[ReconciliationOut])
def list_records(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ReconciliationRecord).filter(
        ReconciliationRecord.user_id == user.id
    ).order_by(ReconciliationRecord.created_at.desc()).all()


@router.post("", response_model=ReconciliationOut, status_code=201)
def create_reconciliation(
    data: ReconciliationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = reconcile_provider(
        db=db,
        user_id=user.id,
        provider=data.provider,
        period_start=data.period_start,
        period_end=data.period_end,
        actual_total=data.actual_total,
        notes=data.notes,
    )
    return record
