"""
Tests for: cost calculations, rounding, duplicate prevention,
subscription allocation limits, timer behavior, and account isolation.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import User, AIPricing
from app.auth import hash_password
from app.services.timer_service import apply_rounding

# Test database
TEST_DB = "sqlite:///./data/test.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    # Create test users
    u1 = User(id="test_u1", email="test1@test.com", password_hash=hash_password("testpass1"), display_name="Test User 1")
    u2 = User(id="test_u2", email="test2@test.com", password_hash=hash_password("testpass2"), display_name="Test User 2")
    # Pricing
    p = AIPricing(provider="openai", model="gpt-4o", input_price_per_million=Decimal("2.50"), output_price_per_million=Decimal("10.00"), cached_input_price_per_million=Decimal("1.25"), effective_date=datetime(2024, 1, 1, tzinfo=timezone.utc))
    db.add_all([u1, u2, p])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def login(email="test1@test.com", password="testpass1"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.cookies


# ── Rounding tests ─────────────────────────────────────────────────────

class TestRounding:
    def test_no_rounding(self):
        assert apply_rounding(754, "none") == 754

    def test_nearest_15(self):
        assert apply_rounding(600, "nearest_15") == 900  # 10 min → 15
        assert apply_rounding(420, "nearest_15") == 0    # 7 min → 0
        assert apply_rounding(480, "nearest_15") == 900  # 8 min → 15 (rounds up at midpoint)
        assert apply_rounding(900, "nearest_15") == 900  # 15 min → 15

    def test_nearest_6(self):
        assert apply_rounding(300, "nearest_6") == 360   # 5 min → 6
        assert apply_rounding(180, "nearest_6") == 360   # 3 min → 6 (rounds up at midpoint)

    def test_up_15(self):
        assert apply_rounding(1, "up_15") == 900         # 1 sec → 15 min
        assert apply_rounding(900, "up_15") == 900       # exactly 15 min stays
        assert apply_rounding(901, "up_15") == 1800      # 15:01 → 30 min

    def test_zero_duration(self):
        assert apply_rounding(0, "nearest_15") == 0
        assert apply_rounding(0, "up_15") == 0


# ── Timer behavior ─────────────────────────────────────────────────────

class TestTimers:
    def test_start_stop(self):
        cookies = login()
        # Create customer and job
        r = client.post("/api/customers", json={"name": "Timer Test Client", "default_hourly_rate": 100}, cookies=cookies)
        cid = r.json()["id"]
        r = client.post("/api/jobs", json={"customer_id": cid, "title": "Timer Test Job"}, cookies=cookies)
        jid = r.json()["id"]

        # Start timer
        r = client.post("/api/timers/start", json={"job_id": jid}, cookies=cookies)
        assert r.status_code == 200
        tid = r.json()["id"]

        # Active timers
        r = client.get("/api/timers/active", cookies=cookies)
        assert len(r.json()) == 1

        # Stop timer
        r = client.post("/api/timers/stop", json={"timer_id": tid, "rounding_rule": "nearest_15"}, cookies=cookies)
        assert r.status_code == 200
        assert r.json()["duration_seconds"] is not None

    def test_overlapping_timer_prevention(self):
        cookies = login()
        r = client.post("/api/customers", json={"name": "Overlap Test", "default_hourly_rate": 100}, cookies=cookies)
        cid = r.json()["id"]
        r = client.post("/api/jobs", json={"customer_id": cid, "title": "Overlap Job 1"}, cookies=cookies)
        jid1 = r.json()["id"]
        r = client.post("/api/jobs", json={"customer_id": cid, "title": "Overlap Job 2"}, cookies=cookies)
        jid2 = r.json()["id"]

        client.post("/api/timers/start", json={"job_id": jid1}, cookies=cookies)
        r = client.post("/api/timers/start", json={"job_id": jid2}, cookies=cookies)
        assert r.status_code == 400
        assert "already running" in r.json()["detail"].lower()


# ── Duplicate prevention ───────────────────────────────────────────────

class TestDuplicatePrevention:
    def test_duplicate_api_request_id(self):
        cookies = login()
        r = client.post("/api/customers", json={"name": "Dup Test", "default_hourly_rate": 100}, cookies=cookies)
        cid = r.json()["id"]
        r = client.post("/api/jobs", json={"customer_id": cid, "title": "Dup Job"}, cookies=cookies)
        jid = r.json()["id"]

        usage = {"job_id": jid, "provider": "openai", "model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "provider_request_id": "unique-req-123"}

        r = client.post("/api/ai/usage", json=usage, cookies=cookies)
        assert r.status_code == 201

        r = client.post("/api/ai/usage", json=usage, cookies=cookies)
        assert r.status_code == 409
        assert "duplicate" in r.json()["detail"].lower()


# ── Subscription allocation limits ─────────────────────────────────────

class TestSubscriptionLimits:
    def test_cannot_exceed_100_percent(self):
        cookies = login()
        r = client.post("/api/customers", json={"name": "Sub Limit Test", "default_hourly_rate": 100}, cookies=cookies)
        cid = r.json()["id"]
        r = client.post("/api/jobs", json={"customer_id": cid, "title": "Sub Job 1"}, cookies=cookies)
        jid1 = r.json()["id"]
        r = client.post("/api/jobs", json={"customer_id": cid, "title": "Sub Job 2"}, cookies=cookies)
        jid2 = r.json()["id"]

        r = client.post("/api/subscriptions", json={"provider": "OpenAI", "plan_name": "Test", "monthly_cost": 20}, cookies=cookies)
        sid = r.json()["id"]

        alloc = {"subscription_id": sid, "job_id": jid1, "period_start": "2026-10-01T00:00:00Z", "period_end": "2026-10-31T23:59:59Z", "allocation_percentage": 70}
        r = client.post("/api/subscriptions/allocations", json=alloc, cookies=cookies)
        assert r.status_code == 201
        assert float(r.json()["allocated_amount"]) == 14.00

        alloc2 = {**alloc, "job_id": jid2, "allocation_percentage": 40}
        r = client.post("/api/subscriptions/allocations", json=alloc2, cookies=cookies)
        assert r.status_code == 400
        assert "exceed 100%" in r.json()["detail"].lower() or "110" in r.json()["detail"]


# ── Account isolation ──────────────────────────────────────────────────

class TestAccountIsolation:
    def test_user2_cannot_see_user1_data(self):
        c1 = login("test1@test.com", "testpass1")
        c2 = login("test2@test.com", "testpass2")

        client.post("/api/customers", json={"name": "User1 Client", "default_hourly_rate": 100}, cookies=c1)

        r = client.get("/api/customers", cookies=c2)
        assert len(r.json()) == 0

    def test_user2_cannot_access_user1_customer(self):
        c1 = login("test1@test.com", "testpass1")
        r = client.post("/api/customers", json={"name": "Private Client", "default_hourly_rate": 100}, cookies=c1)
        cid = r.json()["id"]

        c2 = login("test2@test.com", "testpass2")
        r = client.get(f"/api/customers/{cid}", cookies=c2)
        assert r.status_code == 404


# ── Cost calculation tests ─────────────────────────────────────────────

class TestCostCalculation:
    def test_hourly_job_cost(self):
        cookies = login()
        r = client.post("/api/customers", json={"name": "Cost Test Client", "default_hourly_rate": 100, "default_internal_cost_rate": 30}, cookies=cookies)
        cid = r.json()["id"]
        r = client.post("/api/jobs", json={"customer_id": cid, "title": "Cost Test Job", "markup_percent": 10}, cookies=cookies)
        jid = r.json()["id"]

        # Add 2 hours billable time
        now = datetime.now(timezone.utc)
        client.post("/api/timers/entries", json={
            "job_id": jid,
            "start_time": (now - timedelta(hours=2)).isoformat(),
            "end_time": now.isoformat(),
            "is_billable": True,
            "rounding_rule": "none",
        }, cookies=cookies)

        # Add API usage
        client.post("/api/ai/usage", json={
            "job_id": jid, "provider": "openai", "model": "gpt-4o",
            "input_tokens": 10000, "output_tokens": 5000,
            "provider_request_id": "cost-test-001",
        }, cookies=cookies)

        r = client.get(f"/api/jobs/{jid}/cost", cookies=cookies)
        assert r.status_code == 200
        cost = r.json()

        # 2 hours * $100/hr = $200 billable
        assert float(cost["billable_labor"]) == 200.00
        # 2 hours * $30/hr internal = $60
        assert float(cost["internal_labor_cost"]) == 60.00
        # Profit should be positive
        assert float(cost["profit"]) > 0


# ── Export test ────────────────────────────────────────────────────────

class TestExport:
    def test_csv_export(self):
        cookies = login()
        r = client.get("/api/reports/export/billing", cookies=cookies)
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "Job ID" in r.text
