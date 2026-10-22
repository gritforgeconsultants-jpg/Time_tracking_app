import csv
import io
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models import Job, Customer, TimeEntry
from app.services.cost_calculator import calculate_job_cost


def export_billing_csv(db: Session, user_id: str, job_ids: list[str] | None = None) -> str:
    query = db.query(Job).filter(Job.user_id == user_id)
    if job_ids:
        query = query.filter(Job.id.in_(job_ids))

    jobs = query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Job ID", "Job Title", "Customer", "Job Type", "Status",
        "Billable Hours", "Billable Labor", "Internal Labor Cost",
        "API Costs", "Subscription Costs", "Phone Costs",
        "Total Internal Cost", "Customer Charge", "Profit", "Margin %",
        "Budget", "Budget Remaining",
    ])

    for job in jobs:
        summary = calculate_job_cost(db, job.id, user_id)
        writer.writerow([
            summary.job_id,
            summary.job_title,
            summary.customer_name,
            summary.job_type,
            job.status,
            f"{summary.billable_hours:.4f}",
            f"{summary.billable_labor:.2f}",
            f"{summary.internal_labor_cost:.2f}",
            f"{summary.api_costs:.2f}",
            f"{summary.subscription_costs:.2f}",
            f"{summary.phone_costs:.2f}",
            f"{summary.total_internal_cost:.2f}",
            f"{summary.customer_charge:.2f}",
            f"{summary.profit:.2f}",
            f"{summary.margin_percent:.2f}" if summary.margin_percent is not None else "N/A",
            f"{summary.budget:.2f}" if summary.budget else "N/A",
            f"{summary.budget_remaining:.2f}" if summary.budget_remaining is not None else "N/A",
        ])

    return output.getvalue()


def export_time_entries_csv(db: Session, user_id: str, job_id: str | None = None) -> str:
    query = db.query(TimeEntry).filter(TimeEntry.user_id == user_id)
    if job_id:
        query = query.filter(TimeEntry.job_id == job_id)

    entries = query.order_by(TimeEntry.start_time).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Entry ID", "Job ID", "Start Time (UTC)", "End Time (UTC)",
        "Duration (seconds)", "Rounded Duration (seconds)", "Rounding Rule",
        "Billable", "Billed", "Notes",
    ])

    for e in entries:
        writer.writerow([
            e.id,
            e.job_id,
            e.start_time.isoformat() if e.start_time else "",
            e.end_time.isoformat() if e.end_time else "",
            e.duration_seconds or "",
            e.rounded_duration_seconds or "",
            e.rounding_rule,
            "Yes" if e.is_billable else "No",
            "Yes" if e.is_billed else "No",
            e.notes or "",
        ])

    return output.getvalue()
