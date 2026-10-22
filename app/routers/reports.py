from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from decimal import Decimal
from datetime import datetime
from app.database import get_db
from app.models import (
    User, Job, Customer, TimeEntry, AIAPIUsage,
    SubscriptionAllocation, VerizonCallRecord, VerizonPlanAllocation, AISubscription,
)
from app.auth import get_current_user
from app.services.cost_calculator import calculate_job_cost
from app.services.export_service import export_billing_csv, export_time_entries_csv

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.user_id == user.id, Job.status == "active").all()
    job_summaries = []
    for j in jobs:
        try:
            summary = calculate_job_cost(db, j.id, user.id)
            job_summaries.append(summary.model_dump())
        except Exception:
            pass

    # Provider spending totals
    provider_spending = db.query(
        AIAPIUsage.provider,
        func.sum(AIAPIUsage.calculated_cost),
        func.count(AIAPIUsage.id),
    ).filter(AIAPIUsage.user_id == user.id).group_by(AIAPIUsage.provider).all()

    # Unassigned expenses
    unassigned_calls = db.query(func.count(VerizonCallRecord.id)).filter(
        VerizonCallRecord.user_id == user.id,
        VerizonCallRecord.job_id.is_(None),
    ).scalar()

    # Budget alerts
    budget_alerts = []
    for s in job_summaries:
        if s.get("budget") and s.get("budget_remaining") is not None:
            remaining_pct = float(s["budget_remaining"]) / float(s["budget"]) * 100 if float(s["budget"]) > 0 else 100
            if remaining_pct < 20:
                budget_alerts.append({
                    "job_id": s["job_id"],
                    "job_title": s["job_title"],
                    "budget": str(s["budget"]),
                    "remaining": str(s["budget_remaining"]),
                    "remaining_pct": round(remaining_pct, 1),
                })

    return {
        "active_jobs": len(jobs),
        "job_summaries": job_summaries,
        "provider_spending": [
            {"provider": p, "total_cost": str(c or 0), "request_count": n}
            for p, c, n in provider_spending
        ],
        "unassigned_verizon_calls": unassigned_calls,
        "budget_alerts": budget_alerts,
    }


@router.get("/monthly")
def monthly_totals(
    year: int | None = None,
    month: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    y = year or now.year
    m = month or now.month

    # Revenue per customer
    customers = db.query(Customer).filter(Customer.user_id == user.id).all()
    result = []
    for cust in customers:
        jobs = db.query(Job).filter(Job.customer_id == cust.id).all()
        total_revenue = Decimal("0")
        total_cost = Decimal("0")
        for j in jobs:
            try:
                s = calculate_job_cost(db, j.id, user.id)
                total_revenue += s.customer_charge
                total_cost += s.total_internal_cost
            except Exception:
                pass
        if total_revenue > 0 or total_cost > 0:
            result.append({
                "customer_id": cust.id,
                "customer_name": cust.name,
                "total_revenue": str(total_revenue),
                "total_cost": str(total_cost),
                "profit": str(total_revenue - total_cost),
            })

    return {"year": y, "month": m, "customers": result}


@router.get("/export/billing")
def export_billing(
    job_ids: str | None = Query(None, description="Comma-separated job IDs"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ids = job_ids.split(",") if job_ids else None
    csv_data = export_billing_csv(db, user.id, ids)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=billing_report.csv"},
    )


@router.get("/export/time")
def export_time(
    job_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    csv_data = export_time_entries_csv(db, user.id, job_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=time_entries.csv"},
    )
