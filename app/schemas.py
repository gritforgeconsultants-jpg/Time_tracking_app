from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field


# ── Auth ────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str
    timezone: str = "America/New_York"

class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    timezone: str
    currency: str
    created_at: datetime
    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginForm(BaseModel):
    email: EmailStr
    password: str


# ── Customers ───────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    default_hourly_rate: Decimal = Decimal("0")
    default_internal_cost_rate: Optional[Decimal] = None
    notes: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    default_hourly_rate: Optional[Decimal] = None
    default_internal_cost_rate: Optional[Decimal] = None
    notes: Optional[str] = None

class CustomerOut(BaseModel):
    id: str
    name: str
    company: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    default_hourly_rate: Decimal
    default_internal_cost_rate: Optional[Decimal]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Jobs ────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    customer_id: str
    title: str
    description: Optional[str] = None
    job_type: str = "hourly"
    hourly_rate: Optional[Decimal] = None
    internal_cost_rate: Optional[Decimal] = None
    fixed_price: Optional[Decimal] = None
    budget: Optional[Decimal] = None
    markup_percent: Decimal = Decimal("0")
    billing_notes: Optional[str] = None

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    job_type: Optional[str] = None
    hourly_rate: Optional[Decimal] = None
    internal_cost_rate: Optional[Decimal] = None
    fixed_price: Optional[Decimal] = None
    budget: Optional[Decimal] = None
    markup_percent: Optional[Decimal] = None
    billing_notes: Optional[str] = None

class JobOut(BaseModel):
    id: str
    customer_id: str
    title: str
    description: Optional[str]
    status: str
    job_type: str
    hourly_rate: Optional[Decimal]
    internal_cost_rate: Optional[Decimal]
    fixed_price: Optional[Decimal]
    budget: Optional[Decimal]
    markup_percent: Decimal
    billing_notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Time entries ────────────────────────────────────────────────────────

class TimerStart(BaseModel):
    job_id: str
    notes: Optional[str] = None
    is_billable: bool = True

class TimerStop(BaseModel):
    timer_id: str
    notes: Optional[str] = None
    rounding_rule: str = "none"

class TimeEntryCreate(BaseModel):
    job_id: str
    start_time: datetime
    end_time: datetime
    is_billable: bool = True
    notes: Optional[str] = None
    rounding_rule: str = "none"

class TimeEntryUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_billable: Optional[bool] = None
    notes: Optional[str] = None
    rounding_rule: Optional[str] = None

class TimeEntryOut(BaseModel):
    id: str
    job_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    is_billable: bool
    notes: Optional[str]
    rounding_rule: str
    rounded_duration_seconds: Optional[int]
    is_billed: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class ActiveTimerOut(BaseModel):
    id: str
    job_id: str
    start_time: datetime
    notes: Optional[str]
    is_billable: bool
    job_title: Optional[str] = None
    customer_name: Optional[str] = None
    elapsed_seconds: Optional[int] = None
    model_config = {"from_attributes": True}


# ── AI API usage ────────────────────────────────────────────────────────

class AIUsageCreate(BaseModel):
    job_id: str
    provider: str
    model: str
    provider_request_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    other_units: Optional[dict] = None
    duration_ms: Optional[int] = None
    status: str = "success"
    calculated_cost: Optional[Decimal] = None
    cost_is_estimated: bool = True

class AIUsageOut(BaseModel):
    id: str
    job_id: str
    provider: str
    model: str
    provider_request_id: Optional[str]
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    other_units: Optional[dict]
    duration_ms: Optional[int]
    status: str
    calculated_cost: Decimal
    cost_currency: str
    cost_is_estimated: bool
    reconciled: bool
    reconciled_cost: Optional[Decimal]
    is_billed: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── AI subscriptions ───────────────────────────────────────────────────

class SubscriptionCreate(BaseModel):
    provider: str
    plan_name: str
    monthly_cost: Decimal
    currency: str = "USD"
    billing_cycle_day: int = 1
    notes: Optional[str] = None

class SubscriptionUpdate(BaseModel):
    plan_name: Optional[str] = None
    monthly_cost: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class SubscriptionOut(BaseModel):
    id: str
    provider: str
    plan_name: str
    monthly_cost: Decimal
    currency: str
    billing_cycle_day: int
    status: str
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}

class AllocationCreate(BaseModel):
    subscription_id: str
    job_id: str
    period_start: datetime
    period_end: datetime
    allocation_method: str = "fixed_percentage"
    allocation_percentage: Decimal
    notes: Optional[str] = None

class AllocationOut(BaseModel):
    id: str
    subscription_id: str
    job_id: str
    period_start: datetime
    period_end: datetime
    allocation_method: str
    allocation_percentage: Decimal
    allocated_amount: Decimal
    is_billed: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Verizon ─────────────────────────────────────────────────────────────

class VerizonImportOut(BaseModel):
    id: str
    filename: str
    import_date: datetime
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    total_amount: Optional[Decimal]
    status: str
    record_count: int = 0
    created_at: datetime
    model_config = {"from_attributes": True}

class VerizonCallOut(BaseModel):
    id: str
    import_id: str
    phone_number: Optional[str]
    call_date: Optional[datetime]
    duration_seconds: int
    call_type: Optional[str]
    charge_amount: Decimal
    job_id: Optional[str]
    customer_id: Optional[str]
    is_reviewed: bool
    is_billed: bool
    model_config = {"from_attributes": True}

class VerizonCallAssign(BaseModel):
    job_id: Optional[str] = None
    customer_id: Optional[str] = None
    is_reviewed: bool = True

class VerizonPlanAllocCreate(BaseModel):
    job_id: str
    period_start: datetime
    period_end: datetime
    allocation_percentage: Decimal
    plan_total: Decimal

class VerizonPlanAllocOut(BaseModel):
    id: str
    job_id: str
    period_start: datetime
    period_end: datetime
    allocation_percentage: Decimal
    allocated_amount: Decimal
    plan_total: Decimal
    is_billed: bool
    model_config = {"from_attributes": True}


# ── Pricing ─────────────────────────────────────────────────────────────

class PricingCreate(BaseModel):
    provider: str
    model: str
    input_price_per_million: Decimal
    output_price_per_million: Decimal
    cached_input_price_per_million: Optional[Decimal] = None
    effective_date: datetime
    end_date: Optional[datetime] = None
    notes: Optional[str] = None

class PricingOut(BaseModel):
    id: int
    provider: str
    model: str
    input_price_per_million: Decimal
    output_price_per_million: Decimal
    cached_input_price_per_million: Optional[Decimal]
    effective_date: datetime
    end_date: Optional[datetime]
    model_config = {"from_attributes": True}


# ── Reconciliation ──────────────────────────────────────────────────────

class ReconciliationCreate(BaseModel):
    provider: str
    period_start: datetime
    period_end: datetime
    actual_total: Decimal
    notes: Optional[str] = None

class ReconciliationOut(BaseModel):
    id: str
    provider: str
    import_date: datetime
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    expected_total: Optional[Decimal]
    actual_total: Optional[Decimal]
    discrepancy: Optional[Decimal]
    status: str
    notes: Optional[str]
    model_config = {"from_attributes": True}


# ── Reports / cost summaries ───────────────────────────────────────────

class JobCostSummary(BaseModel):
    job_id: str
    job_title: str
    customer_name: str
    job_type: str
    billable_hours: Decimal
    billable_labor: Decimal  # hours × customer rate
    internal_labor_cost: Decimal  # hours × internal rate
    api_costs: Decimal
    subscription_costs: Decimal
    phone_costs: Decimal  # verizon call charges + plan allocations
    total_internal_cost: Decimal
    customer_charge: Decimal
    profit: Decimal
    margin_percent: Optional[Decimal]
    budget: Optional[Decimal]
    budget_remaining: Optional[Decimal]
