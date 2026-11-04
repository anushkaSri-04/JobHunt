import os
from pathlib import Path
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select,func
from starlette.middleware.sessions import SessionMiddleware
from . import models as m
from .db import get_db, engine, Base
from .runner import load_config

ph = PasswordHasher()
BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

SECRET = os.getenv("SESSION_SECRET", "")
if len(SECRET) < 32:
    raise RuntimeError("Set SESSION_SECRET (32+ chars) in .env")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)  # no public API docs
app.add_middleware(SessionMiddleware, secret_key=SECRET, https_only=os.getenv("HTTPS_ONLY", "0") == "1",
                   same_site="strict", max_age=60 * 60 * 24 * 14)


@app.on_event("startup")
def init():
    Base.metadata.create_all(engine)  # swap for Alembic migrations in Phase 2


def current_user(request: Request):
    return request.session.get("uid")


class NeedLogin(Exception):
    pass


@app.exception_handler(NeedLogin)
def _login_redirect(request, exc):
    return RedirectResponse("/login", status_code=303)


def require_login(request: Request):
    if not current_user(request):
        raise NeedLogin()


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


# naive per-process throttle; fine for a single private user
_fails: dict[str, int] = {}


@app.post("/login")
def login(request: Request, username: str = Form(), password: str = Form(), db=Depends(get_db)):
    ip = request.client.host if request.client else "?"
    if _fails.get(ip, 0) >= 5:
        return templates.TemplateResponse(request, "login.html", {"error": "Too many attempts. Restart the app to reset."}, status_code=429)
    user = db.scalar(select(m.AppUser).where(m.AppUser.username == username))
    try:
        if not user:
            raise VerifyMismatchError()
        ph.verify(user.password_hash, password)
    except VerifyMismatchError:
        _fails[ip] = _fails.get(ip, 0) + 1
        return templates.TemplateResponse(request, "login.html", {"error": "Invalid credentials."}, status_code=401)
    _fails.pop(ip, None)
    request.session["uid"] = user.id
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", dependencies=[Depends(require_login)])
def feed(request: Request, db=Depends(get_db)):
    threshold = float(load_config().get("skill_match_threshold", 0.5))
    visible = (m.Job.status != "skipped") 
    jobs = db.scalars(
        select(m.Job).where(visible)
        .order_by(m.Job.match_pct.desc().nulls_last(), m.Job.first_seen.desc())
    ).all()
    last = db.scalar(select(m.Run).order_by(m.Run.id.desc()).limit(1))

    def count(model, *conds):
        q = select(func.count()).select_from(model)
        return db.scalar(q.where(*conds) if conds else q)

    stats = {
        "total": count(m.Job),
        "shown": len(jobs),
        "below": count(m.Job, m.Job.match_pct.is_not(None), m.Job.match_pct < threshold),
        "applied": count(m.Job, m.Job.status == "applied"),
        "skipped": count(m.Job, m.Job.status == "skipped"),
        "boards": count(m.Company, m.Company.enabled),
        "dead": count(m.Company, m.Company.enabled, m.Company.zero_days >= 1),
        "threshold": round(threshold * 100),
    }
    return templates.TemplateResponse(request, "feed.html", {"jobs": jobs, "run": last, "stats": stats})


@app.post("/jobs/status", dependencies=[Depends(require_login)])
def set_status(job_id: str = Form(), status: str = Form(), db=Depends(get_db)):
    if status in {"new", "applied", "skipped"} and (job := db.get(m.Job, job_id)):
        job.status = status
        db.commit()
    return RedirectResponse("/", status_code=303)