import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.database import init_db, get_connection
from app.deps import require_page_user
from app.routers import auth, pages, eod, vision

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="EOD Reports")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-only-change-me"),
    max_age=60 * 60 * 12,  # 12 hour session
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(eod.router)
app.include_router(vision.router)


@app.on_event("startup")
def on_startup():
    init_db()


# ---- Page routes (server-rendered shells; data is fetched client-side) ----

@app.get("/login")
def login_page(request: Request, error: int = 0):
    if require_page_user(request):
        return RedirectResponse(url="/")
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": bool(error)}
    )


@app.get("/")
def dashboard(request: Request):
    user = require_page_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": user}
    )


@app.get("/eod/new")
def eod_new(request: Request):
    user = require_page_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "eod_form.html", {"request": request, "user": user}
    )


@app.get("/history")
def history_page(request: Request):
    user = require_page_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "history.html", {"request": request, "user": user}
    )


@app.get("/eod/{eod_id}")
def eod_detail_page(request: Request, eod_id: int):
    user = require_page_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "eod_detail.html", {"request": request, "user": user, "eod_id": eod_id}
    )
