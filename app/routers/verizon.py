import io
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    User, VerizonImport, VerizonCallRecord, VerizonPlanAllocation, Job, Customer,
)
from app.schemas import (
    VerizonImportOut, VerizonCallOut, VerizonCallAssign,
    VerizonPlanAllocCreate, VerizonPlanAllocOut,
)
from app.auth import get_current_user
from app.services.verizon_processor import import_verizon_csv, preview_import

router = APIRouter(prefix="/api/verizon", tags=["verizon"])


@router.get("/imports", response_model=list[VerizonImportOut])
def list_imports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    imports = db.query(VerizonImport).filter(VerizonImport.user_id == user.id).order_by(VerizonImport.created_at.desc()).all()
    result = []
    for imp in imports:
        count = db.query(VerizonCallRecord).filter(VerizonCallRecord.import_id == imp.id).count()
        out = VerizonImportOut(
            id=imp.id,
            filename=imp.filename,
            import_date=imp.import_date,
            period_start=imp.period_start,
            period_end=imp.period_end,
            total_amount=imp.total_amount,
            status=imp.status,
            record_count=count,
            created_at=imp.created_at,
        )
        result.append(out)
    return result


@router.post("/preview")
async def preview(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    raw = (await file.read()).decode("utf-8-sig")
    return preview_import(raw)


@router.post("/import", response_model=VerizonImportOut)
async def do_import(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw = (await file.read()).decode("utf-8-sig")
    imp = import_verizon_csv(db, user.id, file.filename or "upload.csv", raw)
    count = db.query(VerizonCallRecord).filter(VerizonCallRecord.import_id == imp.id).count()
    return VerizonImportOut(
        id=imp.id,
        filename=imp.filename,
        import_date=imp.import_date,
        period_start=imp.period_start,
        period_end=imp.period_end,
        total_amount=imp.total_amount,
        status=imp.status,
        record_count=count,
        created_at=imp.created_at,
    )


@router.get("/calls", response_model=list[VerizonCallOut])
def list_calls(
    import_id: str | None = None,
    unassigned: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(VerizonCallRecord).filter(VerizonCallRecord.user_id == user.id)
    if import_id:
        q = q.filter(VerizonCallRecord.import_id == import_id)
    if unassigned:
        q = q.filter(VerizonCallRecord.job_id.is_(None))
    return q.order_by(VerizonCallRecord.call_date.desc()).limit(200).all()


@router.patch("/calls/{cid}", response_model=VerizonCallOut)
def assign_call(cid: str, data: VerizonCallAssign, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    call = db.query(VerizonCallRecord).filter(VerizonCallRecord.id == cid, VerizonCallRecord.user_id == user.id).first()
    if not call:
        raise HTTPException(404, "Call record not found")
    if data.job_id:
        job = db.query(Job).filter(Job.id == data.job_id, Job.user_id == user.id).first()
        if not job:
            raise HTTPException(404, "Job not found")
    call.job_id = data.job_id
    call.customer_id = data.customer_id
    call.is_reviewed = data.is_reviewed
    db.commit()
    db.refresh(call)
    return call


@router.get("/plan-allocations", response_model=list[VerizonPlanAllocOut])
def list_plan_allocations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(VerizonPlanAllocation).filter(VerizonPlanAllocation.user_id == user.id).all()


@router.post("/plan-allocations", response_model=VerizonPlanAllocOut, status_code=201)
def create_plan_allocation(data: VerizonPlanAllocCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == data.job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    # Check total allocation for this period doesn't exceed 100%
    existing_pct = db.query(
        func.coalesce(func.sum(VerizonPlanAllocation.allocation_percentage), 0)
    ).filter(
        VerizonPlanAllocation.user_id == user.id,
        VerizonPlanAllocation.period_start == data.period_start,
        VerizonPlanAllocation.period_end == data.period_end,
    ).scalar()

    total_after = Decimal(str(existing_pct)) + data.allocation_percentage
    if total_after > Decimal("100"):
        raise HTTPException(
            400,
            f"Total plan allocation would be {total_after}%. Cannot exceed 100%.",
        )

    allocated = data.plan_total * data.allocation_percentage / Decimal("100")

    alloc = VerizonPlanAllocation(
        user_id=user.id,
        job_id=data.job_id,
        period_start=data.period_start,
        period_end=data.period_end,
        allocation_percentage=data.allocation_percentage,
        allocated_amount=allocated.quantize(Decimal("0.01")),
        plan_total=data.plan_total,
    )
    db.add(alloc)
    db.commit()
    db.refresh(alloc)
    return alloc
