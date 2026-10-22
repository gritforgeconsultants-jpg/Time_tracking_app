"""
Seed demo data — clearly labeled as demo data.
Run: python -m demo.seed_demo_data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.database import Base, engine, SessionLocal
from app.models import (
    User, Customer, Job, TimeEntry, AIPricing, AIAPIUsage,
    AISubscription, SubscriptionAllocation,
    VerizonImport, VerizonCallRecord, VerizonPlanAllocation,
)
from app.auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Clean existing demo data
existing = db.query(User).filter(User.email == "demo@example.com").first()
if existing:
    db.delete(existing)
    db.commit()

# ── Demo User ──────────────────────────────────────────────────────────
user = User(
    id="demo_user_01",
    email="demo@example.com",
    password_hash=hash_password("demo1234"),
    display_name="[DEMO] Alex Demo",
    timezone="America/New_York",
    currency="USD",
)
db.add(user)
db.flush()

# ── Customers ──────────────────────────────────────────────────────────
cust1 = Customer(
    id="demo_cust_1",
    user_id=user.id,
    name="[DEMO] Acme Corp",
    company="Acme Corporation",
    email="billing@acme-demo.example.com",
    phone="555-0101",
    default_hourly_rate=Decimal("150.00"),
    default_internal_cost_rate=Decimal("45.00"),
    notes="Demo customer - consulting client",
)
cust2 = Customer(
    id="demo_cust_2",
    user_id=user.id,
    name="[DEMO] Beta Labs",
    company="Beta Laboratories",
    email="ap@betalabs-demo.example.com",
    phone="555-0202",
    default_hourly_rate=Decimal("175.00"),
    default_internal_cost_rate=Decimal("50.00"),
    notes="Demo customer - AI project client",
)
db.add_all([cust1, cust2])
db.flush()

# ── Jobs ───────────────────────────────────────────────────────────────
now = datetime.now(timezone.utc)
job1 = Job(
    id="demo_job_01",
    user_id=user.id,
    customer_id=cust1.id,
    title="[DEMO] Website Redesign",
    description="Full redesign of corporate website with AI-assisted content generation",
    status="active",
    job_type="hourly",
    hourly_rate=Decimal("150.00"),
    internal_cost_rate=Decimal("45.00"),
    budget=Decimal("15000.00"),
    markup_percent=Decimal("15.00"),
)
job2 = Job(
    id="demo_job_02",
    user_id=user.id,
    customer_id=cust2.id,
    title="[DEMO] AI Chatbot Integration",
    description="Build and deploy customer support chatbot using multiple AI providers",
    status="active",
    job_type="hourly",
    hourly_rate=Decimal("175.00"),
    internal_cost_rate=Decimal("50.00"),
    budget=Decimal("25000.00"),
    markup_percent=Decimal("20.00"),
)
job3 = Job(
    id="demo_job_03",
    user_id=user.id,
    customer_id=cust1.id,
    title="[DEMO] SEO Audit (Fixed)",
    description="Fixed-price SEO audit and recommendations report",
    status="active",
    job_type="fixed_price",
    fixed_price=Decimal("3500.00"),
    internal_cost_rate=Decimal("45.00"),
    budget=Decimal("3500.00"),
)
db.add_all([job1, job2, job3])
db.flush()

# ── Time Entries ───────────────────────────────────────────────────────
entries = [
    TimeEntry(user_id=user.id, job_id=job1.id, start_time=now - timedelta(days=5, hours=8), end_time=now - timedelta(days=5, hours=5), duration_seconds=10800, rounded_duration_seconds=10800, is_billable=True, rounding_rule="nearest_15", notes="[DEMO] Initial design mockups"),
    TimeEntry(user_id=user.id, job_id=job1.id, start_time=now - timedelta(days=4, hours=7), end_time=now - timedelta(days=4, hours=4), duration_seconds=10800, rounded_duration_seconds=10800, is_billable=True, rounding_rule="nearest_15", notes="[DEMO] Content strategy meeting + AI prompts"),
    TimeEntry(user_id=user.id, job_id=job1.id, start_time=now - timedelta(days=3, hours=6), end_time=now - timedelta(days=3, hours=5, minutes=20), duration_seconds=2400, rounded_duration_seconds=2700, is_billable=False, rounding_rule="up_15", notes="[DEMO] Internal research (non-billable)"),
    TimeEntry(user_id=user.id, job_id=job2.id, start_time=now - timedelta(days=4, hours=3), end_time=now - timedelta(days=4, hours=0), duration_seconds=10800, rounded_duration_seconds=10800, is_billable=True, rounding_rule="nearest_15", notes="[DEMO] Chatbot architecture design"),
    TimeEntry(user_id=user.id, job_id=job2.id, start_time=now - timedelta(days=3, hours=8), end_time=now - timedelta(days=3, hours=3), duration_seconds=18000, rounded_duration_seconds=18000, is_billable=True, rounding_rule="nearest_15", notes="[DEMO] API integration — OpenAI + Anthropic"),
    TimeEntry(user_id=user.id, job_id=job2.id, start_time=now - timedelta(days=2, hours=6), end_time=now - timedelta(days=2, hours=4, minutes=10), duration_seconds=6600, rounded_duration_seconds=6300, is_billable=True, rounding_rule="nearest_15", notes="[DEMO] Testing and prompt refinement"),
    TimeEntry(user_id=user.id, job_id=job3.id, start_time=now - timedelta(days=2, hours=2), end_time=now - timedelta(days=2), duration_seconds=7200, rounded_duration_seconds=7200, is_billable=True, rounding_rule="none", notes="[DEMO] SEO audit - technical analysis"),
]
db.add_all(entries)

# ── AI Pricing Tables ─────────────────────────────────────────────────
pricing_data = [
    AIPricing(provider="openai", model="gpt-4o", input_price_per_million=Decimal("2.50"), output_price_per_million=Decimal("10.00"), cached_input_price_per_million=Decimal("1.25"), effective_date=datetime(2024, 10, 1, tzinfo=timezone.utc)),
    AIPricing(provider="openai", model="gpt-4o-mini", input_price_per_million=Decimal("0.15"), output_price_per_million=Decimal("0.60"), cached_input_price_per_million=Decimal("0.075"), effective_date=datetime(2024, 7, 1, tzinfo=timezone.utc)),
    AIPricing(provider="anthropic", model="claude-sonnet-4-20250514", input_price_per_million=Decimal("3.00"), output_price_per_million=Decimal("15.00"), cached_input_price_per_million=Decimal("0.30"), effective_date=datetime(2025, 5, 14, tzinfo=timezone.utc)),
    AIPricing(provider="anthropic", model="claude-haiku-3-5-20241022", input_price_per_million=Decimal("0.80"), output_price_per_million=Decimal("4.00"), cached_input_price_per_million=Decimal("0.08"), effective_date=datetime(2024, 10, 22, tzinfo=timezone.utc)),
    AIPricing(provider="google", model="gemini-2.0-flash", input_price_per_million=Decimal("0.10"), output_price_per_million=Decimal("0.40"), effective_date=datetime(2025, 2, 1, tzinfo=timezone.utc)),
    AIPricing(provider="xai", model="grok-3", input_price_per_million=Decimal("3.00"), output_price_per_million=Decimal("15.00"), effective_date=datetime(2025, 4, 1, tzinfo=timezone.utc)),
]
db.add_all(pricing_data)

# ── AI API Usage ───────────────────────────────────────────────────────
usages = [
    AIAPIUsage(user_id=user.id, job_id=job1.id, provider="openai", model="gpt-4o", provider_request_id="demo-req-001", timestamp=now - timedelta(days=4, hours=6), input_tokens=2500, output_tokens=800, cached_tokens=0, status="success", calculated_cost=Decimal("0.0143"), cost_is_estimated=True),
    AIAPIUsage(user_id=user.id, job_id=job1.id, provider="anthropic", model="claude-sonnet-4-20250514", provider_request_id="demo-req-002", timestamp=now - timedelta(days=4, hours=5), input_tokens=3000, output_tokens=1200, cached_tokens=500, status="success", calculated_cost=Decimal("0.0272"), cost_is_estimated=True),
    AIAPIUsage(user_id=user.id, job_id=job2.id, provider="openai", model="gpt-4o", provider_request_id="demo-req-003", timestamp=now - timedelta(days=3, hours=7), input_tokens=15000, output_tokens=4000, cached_tokens=5000, status="success", calculated_cost=Decimal("0.0838"), cost_is_estimated=True),
    AIAPIUsage(user_id=user.id, job_id=job2.id, provider="anthropic", model="claude-sonnet-4-20250514", provider_request_id="demo-req-004", timestamp=now - timedelta(days=3, hours=6), input_tokens=12000, output_tokens=3500, cached_tokens=2000, status="success", calculated_cost=Decimal("0.0891"), cost_is_estimated=True),
    AIAPIUsage(user_id=user.id, job_id=job2.id, provider="google", model="gemini-2.0-flash", provider_request_id="demo-req-005", timestamp=now - timedelta(days=2, hours=5), input_tokens=8000, output_tokens=2000, cached_tokens=0, status="success", calculated_cost=Decimal("0.0016"), cost_is_estimated=True),
    AIAPIUsage(user_id=user.id, job_id=job2.id, provider="xai", model="grok-3", provider_request_id="demo-req-006", timestamp=now - timedelta(days=2, hours=4), input_tokens=5000, output_tokens=1500, cached_tokens=0, status="success", calculated_cost=Decimal("0.0375"), cost_is_estimated=True),
    AIAPIUsage(user_id=user.id, job_id=job2.id, provider="openai", model="gpt-4o", provider_request_id="demo-req-007", timestamp=now - timedelta(days=1, hours=3), input_tokens=1000, output_tokens=0, cached_tokens=0, status="error", calculated_cost=Decimal("0.0025"), cost_is_estimated=True),
]
db.add_all(usages)

# ── AI Subscriptions ──────────────────────────────────────────────────
sub1 = AISubscription(id="demo_sub_01", user_id=user.id, provider="OpenAI", plan_name="ChatGPT Plus", monthly_cost=Decimal("20.00"), status="active")
sub2 = AISubscription(id="demo_sub_02", user_id=user.id, provider="Anthropic", plan_name="Claude Pro", monthly_cost=Decimal("20.00"), status="active")
sub3 = AISubscription(id="demo_sub_03", user_id=user.id, provider="Google", plan_name="Gemini Advanced", monthly_cost=Decimal("19.99"), status="active")
sub4 = AISubscription(id="demo_sub_04", user_id=user.id, provider="xAI", plan_name="Grok Premium+", monthly_cost=Decimal("30.00"), status="active")
db.add_all([sub1, sub2, sub3, sub4])
db.flush()

# Subscription allocations
period_start = (now.replace(day=1, hour=0, minute=0, second=0, microsecond=0))
period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

allocs = [
    SubscriptionAllocation(subscription_id=sub1.id, job_id=job1.id, period_start=period_start, period_end=period_end, allocation_method="fixed_percentage", allocation_percentage=Decimal("40"), allocated_amount=Decimal("8.00")),
    SubscriptionAllocation(subscription_id=sub1.id, job_id=job2.id, period_start=period_start, period_end=period_end, allocation_method="fixed_percentage", allocation_percentage=Decimal("60"), allocated_amount=Decimal("12.00")),
    SubscriptionAllocation(subscription_id=sub2.id, job_id=job2.id, period_start=period_start, period_end=period_end, allocation_method="fixed_percentage", allocation_percentage=Decimal("75"), allocated_amount=Decimal("15.00")),
    SubscriptionAllocation(subscription_id=sub2.id, job_id=job3.id, period_start=period_start, period_end=period_end, allocation_method="fixed_percentage", allocation_percentage=Decimal("25"), allocated_amount=Decimal("5.00")),
]
db.add_all(allocs)

# ── Verizon Data ──────────────────────────────────────────────────────
vz_import = VerizonImport(
    id="demo_vz_01",
    user_id=user.id,
    filename="[DEMO] verizon_october_2026.csv",
    period_start=period_start,
    period_end=period_end,
    total_amount=Decimal("127.50"),
    status="reviewed",
    raw_data="Phone Number,Date,Duration (sec),Type,Charge\n555-0101,10/15/2026,360,voice,$2.50\n555-0202,10/16/2026,180,voice,$1.25\n555-0303,10/17/2026,0,text,$0.10\n",
    column_mapping={"phone_number": "Phone Number", "call_date": "Date", "duration_seconds": "Duration (sec)", "call_type": "Type", "charge_amount": "Charge"},
)
db.add(vz_import)
db.flush()

vz_calls = [
    VerizonCallRecord(import_id=vz_import.id, user_id=user.id, phone_number="555-0101", call_date=now - timedelta(days=7), duration_seconds=360, call_type="voice", charge_amount=Decimal("2.50"), job_id=job1.id, customer_id=cust1.id, is_reviewed=True),
    VerizonCallRecord(import_id=vz_import.id, user_id=user.id, phone_number="555-0202", call_date=now - timedelta(days=6), duration_seconds=180, call_type="voice", charge_amount=Decimal("1.25"), job_id=job2.id, customer_id=cust2.id, is_reviewed=True),
    VerizonCallRecord(import_id=vz_import.id, user_id=user.id, phone_number="555-0303", call_date=now - timedelta(days=5), duration_seconds=0, call_type="text", charge_amount=Decimal("0.10"), is_reviewed=False),
]
db.add_all(vz_calls)

# Verizon plan allocation
vz_plan = VerizonPlanAllocation(
    user_id=user.id,
    job_id=job1.id,
    period_start=period_start,
    period_end=period_end,
    allocation_percentage=Decimal("30"),
    allocated_amount=Decimal("38.25"),
    plan_total=Decimal("127.50"),
)
db.add(vz_plan)

db.commit()
db.close()

print("Demo data seeded successfully!")
print("Login: demo@example.com / demo1234")
print("All demo data is prefixed with [DEMO]")
