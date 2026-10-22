from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import (
    Job, TimeEntry, AIAPIUsage, SubscriptionAllocation,
    VerizonCallRecord, VerizonPlanAllocation, Customer,
)
from app.schemas import JobCostSummary

ZERO = Decimal("0")
CENT = Decimal("0.01")
HOUR = Decimal("3600")


def round_currency(val: Decimal) -> Decimal:
    return val.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_job_cost(db: Session, job_id: str, user_id: str) -> JobCostSummary:
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if not job:
        raise ValueError("Job not found")

    customer = db.query(Customer).filter(Customer.id == job.customer_id).first()
    hourly_rate = Decimal(str(job.hourly_rate or customer.default_hourly_rate or 0))
    internal_rate = Decimal(str(job.internal_cost_rate or customer.default_internal_cost_rate or 0))

    # Billable time
    billable_entries = db.query(TimeEntry).filter(
        TimeEntry.job_id == job_id,
        TimeEntry.user_id == user_id,
        TimeEntry.is_billable == True,
    ).all()

    total_billable_seconds = sum(
        (e.rounded_duration_seconds or e.duration_seconds or 0)
        for e in billable_entries
    )
    billable_hours = Decimal(str(total_billable_seconds)) / HOUR

    # All time for internal cost (billable + nonbillable)
    all_entries = db.query(TimeEntry).filter(
        TimeEntry.job_id == job_id,
        TimeEntry.user_id == user_id,
    ).all()
    total_all_seconds = sum(
        (e.rounded_duration_seconds or e.duration_seconds or 0)
        for e in all_entries
    )
    all_hours = Decimal(str(total_all_seconds)) / HOUR

    billable_labor = round_currency(billable_hours * hourly_rate)
    internal_labor_cost = round_currency(all_hours * internal_rate)

    # AI API costs
    api_cost_row = db.query(
        func.coalesce(func.sum(AIAPIUsage.calculated_cost), 0)
    ).filter(
        AIAPIUsage.job_id == job_id,
        AIAPIUsage.user_id == user_id,
    ).scalar()
    api_costs = round_currency(Decimal(str(api_cost_row)))

    # Subscription allocations
    sub_cost_row = db.query(
        func.coalesce(func.sum(SubscriptionAllocation.allocated_amount), 0)
    ).filter(
        SubscriptionAllocation.job_id == job_id,
    ).scalar()
    subscription_costs = round_currency(Decimal(str(sub_cost_row)))

    # Verizon: call charges + plan allocations
    vz_call_row = db.query(
        func.coalesce(func.sum(VerizonCallRecord.charge_amount), 0)
    ).filter(
        VerizonCallRecord.job_id == job_id,
        VerizonCallRecord.user_id == user_id,
    ).scalar()

    vz_plan_row = db.query(
        func.coalesce(func.sum(VerizonPlanAllocation.allocated_amount), 0)
    ).filter(
        VerizonPlanAllocation.job_id == job_id,
        VerizonPlanAllocation.user_id == user_id,
    ).scalar()
    phone_costs = round_currency(Decimal(str(vz_call_row)) + Decimal(str(vz_plan_row)))

    # Totals
    direct_expenses = api_costs + subscription_costs + phone_costs
    total_internal_cost = internal_labor_cost + direct_expenses

    markup = Decimal(str(job.markup_percent or 0))
    markup_on_expenses = round_currency(direct_expenses * markup / Decimal("100"))

    if job.job_type == "fixed_price" and job.fixed_price:
        customer_charge = round_currency(Decimal(str(job.fixed_price)))
    else:
        customer_charge = billable_labor + direct_expenses + markup_on_expenses

    profit = customer_charge - total_internal_cost
    margin_percent = (
        round_currency(profit / customer_charge * Decimal("100"))
        if customer_charge > ZERO else None
    )

    budget = Decimal(str(job.budget)) if job.budget else None
    budget_remaining = round_currency(budget - customer_charge) if budget else None

    return JobCostSummary(
        job_id=job.id,
        job_title=job.title,
        customer_name=customer.name if customer else "Unknown",
        job_type=job.job_type,
        billable_hours=billable_hours.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        billable_labor=billable_labor,
        internal_labor_cost=internal_labor_cost,
        api_costs=api_costs,
        subscription_costs=subscription_costs,
        phone_costs=phone_costs,
        total_internal_cost=total_internal_cost,
        customer_charge=customer_charge,
        profit=profit,
        margin_percent=margin_percent,
        budget=budget,
        budget_remaining=budget_remaining,
    )
