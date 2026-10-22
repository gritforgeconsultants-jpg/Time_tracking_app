import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey,
    Text, Numeric, Index, UniqueConstraint, CheckConstraint, JSON,
)
from sqlalchemy.orm import relationship
from app.database import Base


def gen_id():
    return uuid.uuid4().hex[:12]


def utcnow():
    return datetime.now(timezone.utc)


# ── Users ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String(12), primary_key=True, default=gen_id)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    timezone = Column(String(64), default="America/New_York")
    currency = Column(String(3), default="USD")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    customers = relationship("Customer", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")


# ── Customers ──────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(12), primary_key=True, default=gen_id)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    company = Column(String(255))
    email = Column(String(255))
    phone = Column(String(32))
    default_hourly_rate = Column(Numeric(10, 4), default=Decimal("0"))
    default_internal_cost_rate = Column(Numeric(10, 4))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="customers")
    jobs = relationship("Job", back_populates="customer", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_customers_user", "user_id"),
    )


# ── Jobs ───────────────────────────────────────────────────────────────

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(12), primary_key=True, default=gen_id)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(String(12), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="active")  # active, completed, archived
    job_type = Column(String(20), default="hourly")  # hourly, fixed_price
    hourly_rate = Column(Numeric(10, 4))
    internal_cost_rate = Column(Numeric(10, 4))
    fixed_price = Column(Numeric(12, 2))
    budget = Column(Numeric(12, 2))
    markup_percent = Column(Numeric(6, 2), default=Decimal("0"))
    billing_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="jobs")
    customer = relationship("Customer", back_populates="jobs")
    time_entries = relationship("TimeEntry", back_populates="job", cascade="all, delete-orphan")
    ai_usages = relationship("AIAPIUsage", back_populates="job", cascade="all, delete-orphan")
    subscription_allocations = relationship("SubscriptionAllocation", back_populates="job", cascade="all, delete-orphan")
    verizon_calls = relationship("VerizonCallRecord", back_populates="job")
    verizon_plan_allocations = relationship("VerizonPlanAllocation", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_jobs_user", "user_id"),
        Index("ix_jobs_customer", "customer_id"),
        CheckConstraint("status IN ('active', 'completed', 'archived')", name="ck_job_status"),
        CheckConstraint("job_type IN ('hourly', 'fixed_price')", name="ck_job_type"),
    )


# ── Time entries ───────────────────────────────────────────────────────

class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(String(12), primary_key=True, default=gen_id)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String(12), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    is_billable = Column(Boolean, default=True)
    notes = Column(Text)
    rounding_rule = Column(String(20), default="none")  # none, nearest_15, nearest_6, up_15
    rounded_duration_seconds = Column(Integer)
    is_billed = Column(Boolean, default=False)
    billed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User")
    job = relationship("Job", back_populates="time_entries")

    __table_args__ = (
        Index("ix_time_entries_user_job", "user_id", "job_id"),
        Index("ix_time_entries_start", "start_time"),
    )


# ── Active timers ──────────────────────────────────────────────────────

class ActiveTimer(Base):
    __tablename__ = "active_timers"

    id = Column(String(12), primary_key=True, default=gen_id)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String(12), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    notes = Column(Text)
    is_billable = Column(Boolean, default=True)

    user = relationship("User")
    job = relationship("Job")

    __table_args__ = (
        Index("ix_active_timers_user", "user_id"),
    )


# ── AI pricing tables ─────────────────────────────────────────────────

class AIPricing(Base):
    __tablename__ = "ai_pricing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(32), nullable=False)  # openai, anthropic, google, xai
    model = Column(String(128), nullable=False)
    input_price_per_million = Column(Numeric(12, 6), nullable=False)
    output_price_per_million = Column(Numeric(12, 6), nullable=False)
    cached_input_price_per_million = Column(Numeric(12, 6))
    currency = Column(String(3), default="USD")
    effective_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True))
    notes = Column(Text)

    __table_args__ = (
        Index("ix_ai_pricing_provider_model", "provider", "model"),
    )


# ── AI API usage ───────────────────────────────────────────────────────

class AIAPIUsage(Base):
    __tablename__ = "ai_api_usage"

    id = Column(String(12), primary_key=True, default=gen_id)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String(12), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(32), nullable=False)
    model = Column(String(128), nullable=False)
    provider_request_id = Column(String(255))
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cached_tokens = Column(Integer, default=0)
    other_units = Column(JSON)  # {"audio_seconds": 30, "tool_calls": 2}
    duration_ms = Column(Integer)
    status = Column(String(20), default="success")  # success, error, partial
    calculated_cost = Column(Numeric(12, 6), default=Decimal("0"))
    cost_currency = Column(String(3), default="USD")
    cost_is_estimated = Column(Boolean, default=True)
    reconciled = Column(Boolean, default=False)
    reconciled_cost = Column(Numeric(12, 6))
    reconciled_at = Column(DateTime(timezone=True))
    is_billed = Column(Boolean, default=False)
    billed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User")
    job = relationship("Job", back_populates="ai_usages")

    __table_args__ = (
        Index("ix_ai_usage_user_job", "user_id", "job_id"),
        Index("ix_ai_usage_provider", "provider"),
        UniqueConstraint("provider", "provider_request_id", name="uq_provider_request"),
    )


# ── AI subscriptions ──────────────────────────────────────────────────

class AISubscription(Base):
    __tablename__ = "ai_subscriptions"

    id = Column(String(12), primary_key=True, default=gen_id)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(64), nullable=False)
    plan_name = Column(String(128), nullable=False)
    monthly_cost = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    billing_cycle_day = Column(Integer, default=1)
    status = Column(String(20), default="active")  # active, cancelled
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User")
    allocations = relationship("SubscriptionAllocation", back_populates="subscription", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_subscriptions_user", "user_id"),
    )


# ── Subscription allocations ──────────────────────────────────────────

class SubscriptionAllocation(Base):
    __tablename__ = "subscription_allocations"

    id = Column(String(12), primary_key=True, default=gen_id)
    subscription_id = Column(String(12), ForeignKey("ai_subscriptions.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String(12), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    allocation_method = Column(String(32), default="fixed_percentage")  # time_based, fixed_percentage, manual
    allocation_percentage = Column(Numeric(6, 2), nullable=False)
    allocated_amount = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text)
    is_billed = Column(Boolean, default=False)
    billed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    subscription = relationship("AISubscription", back_populates="allocations")
    job = relationship("Job", back_populates="subscription_allocations")

    __table_args__ = (
        Index("ix_sub_alloc_subscription", "subscription_id"),
        Index("ix_sub_alloc_job", "job_id"),
    )


# ── Verizon imports ───────────────────────────────────────────────────

class VerizonImport(Base):
    __tablename__ = "verizon_imports"

    id = Column(String(12), primary_key=True, default=gen_id)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    import_date = Column(DateTime(timezone=True), default=utcnow)
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    total_amount = Column(Numeric(10, 2))
    status = Column(String(20), default="pending")  # pending, reviewed, applied
    raw_data = Column(Text)  # original CSV preserved
    column_mapping = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User")
    call_records = relationship("VerizonCallRecord", back_populates="import_record", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_verizon_imports_user", "user_id"),
    )


# ── Verizon call records ──────────────────────────────────────────────

class VerizonCallRecord(Base):
    __tablename__ = "verizon_call_records"

    id = Column(String(12), primary_key=True, default=gen_id)
    import_id = Column(String(12), ForeignKey("verizon_imports.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    phone_number = Column(String(32))
    call_date = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer, default=0)
    call_type = Column(String(20))  # voice, text, data
    charge_amount = Column(Numeric(10, 4), default=Decimal("0"))
    job_id = Column(String(12), ForeignKey("jobs.id", ondelete="SET NULL"))
    customer_id = Column(String(12), ForeignKey("customers.id", ondelete="SET NULL"))
    is_reviewed = Column(Boolean, default=False)
    is_billed = Column(Boolean, default=False)
    billed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    import_record = relationship("VerizonImport", back_populates="call_records")
    user = relationship("User")
    job = relationship("Job", back_populates="verizon_calls")
    customer = relationship("Customer")

    __table_args__ = (
        Index("ix_verizon_calls_user", "user_id"),
        Index("ix_verizon_calls_phone", "phone_number"),
    )


# ── Verizon plan allocations ─────────────────────────────────────────

class VerizonPlanAllocation(Base):
    __tablename__ = "verizon_plan_allocations"

    id = Column(String(12), primary_key=True, default=gen_id)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String(12), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    allocation_method = Column(String(32), default="fixed_percentage")
    allocation_percentage = Column(Numeric(6, 2), nullable=False)
    allocated_amount = Column(Numeric(10, 2), nullable=False)
    plan_total = Column(Numeric(10, 2), nullable=False)
    is_billed = Column(Boolean, default=False)
    billed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User")
    job = relationship("Job", back_populates="verizon_plan_allocations")

    __table_args__ = (
        Index("ix_vz_plan_alloc_user", "user_id"),
    )


# ── Reconciliation ───────────────────────────────────────────────────

class ReconciliationRecord(Base):
    __tablename__ = "reconciliation_records"

    id = Column(String(12), primary_key=True, default=gen_id)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(64), nullable=False)
    import_date = Column(DateTime(timezone=True), default=utcnow)
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    expected_total = Column(Numeric(12, 4))
    actual_total = Column(Numeric(12, 4))
    discrepancy = Column(Numeric(12, 4))
    status = Column(String(20), default="pending")  # pending, resolved, flagged
    details = Column(JSON)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User")

    __table_args__ = (
        Index("ix_reconciliation_user", "user_id"),
    )


# ── Audit log ─────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(12), ForeignKey("users.id", ondelete="SET NULL"))
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(12), nullable=False)
    action = Column(String(32), nullable=False)  # create, update, delete, bill, reconcile
    old_values = Column(JSON)
    new_values = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )
