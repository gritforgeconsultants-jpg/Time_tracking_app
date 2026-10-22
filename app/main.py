from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from app.database import Base, engine
from app.auth import get_current_user, get_user_from_token
from app.models import User
from app.routers import (
    auth_router, customers, jobs, timers, ai_usage,
    subscriptions, verizon, reports, reconciliation,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Cost Tracker", version="1.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# API routers
app.include_router(auth_router.router)
app.include_router(customers.router)
app.include_router(jobs.router)
app.include_router(timers.router)
app.include_router(ai_usage.router)
app.include_router(subscriptions.router)
app.include_router(verizon.router)
app.include_router(reports.router)
app.include_router(reconciliation.router)


def get_optional_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        return get_user_from_token(token, db)
    finally:
        db.close()


# Page routes
@app.get("/")
async def index(request: Request):
    user = get_optional_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/customers")
async def customers_page(request: Request):
    user = get_optional_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("customers.html", {"request": request, "user": user})


@app.get("/jobs")
async def jobs_page(request: Request):
    user = get_optional_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("jobs.html", {"request": request, "user": user})


@app.get("/jobs/{job_id}")
async def job_detail_page(request: Request, job_id: str):
    user = get_optional_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("job_detail.html", {"request": request, "user": user, "job_id": job_id})


@app.get("/timers")
async def timers_page(request: Request):
    user = get_optional_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("timers.html", {"request": request, "user": user})


@app.get("/ai-usage")
async def ai_usage_page(request: Request):
    user = get_optional_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("ai_usage.html", {"request": request, "user": user})


@app.get("/subscriptions")
async def subscriptions_page(request: Request):
    user = get_optional_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("subscriptions.html", {"request": request, "user": user})


@app.get("/verizon")
async def verizon_page(request: Request):
    user = get_optional_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("verizon.html", {"request": request, "user": user})


@app.get("/reports")
async def reports_page(request: Request):
    user = get_optional_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("reports.html", {"request": request, "user": user})
