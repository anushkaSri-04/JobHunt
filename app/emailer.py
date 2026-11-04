"""Daily summary email: best-matching jobs not yet emailed, plus a link to the JobHunt site."""
import html
import os

from sqlalchemy import select

from engine.mailer import send   # your SMTP sender, unchanged
from . import models as m
from .runner import load_config


def _card(j: m.Job) -> str:
    sk = j.skills or {}
    missing = (sk.get("req_missing") or [])[:3] or (sk.get("nice_missing") or [])[:3]
    pct = f"{round(j.match_pct * 100)}% match" if j.match_pct is not None else "not scored"
    gap = (f'<div style="font-size:13px;color:#b45309;margin-bottom:10px;">Missing: '
           f'{html.escape(", ".join(missing))}</div>') if missing else ""
    return (
        '<div style="border:1px solid #e5e5e5;border-radius:10px;padding:14px;margin-bottom:10px;">'
        f'<div style="font-size:16px;font-weight:600;color:#111;">{html.escape(j.title)}'
        f' <span style="font-size:13px;color:#15803d;">· {pct}</span></div>'
        f'<div style="font-size:13px;color:#666;margin:4px 0 8px;">'
        f'{html.escape(j.company_name)} · {html.escape(j.location or "—")}</div>'
        f'{gap}'
        f'<a href="{html.escape(j.url or "#")}" style="font-size:14px;color:#111;font-weight:600;">Open posting →</a>'
        '</div>'
    )


def send_daily(db, limit: int = 5) -> str:
    threshold = float(load_config().get("skill_match_threshold", 0.5))
    jobs = db.scalars(
        select(m.Job)
        .where(m.Job.emailed == False, m.Job.status == "new",           # noqa: E712
               m.Job.match_pct.is_not(None), m.Job.match_pct >= threshold)
        .order_by(m.Job.match_pct.desc(), m.Job.first_seen.desc())
        .limit(limit)
    ).all()
    if not jobs:
        return "No new matching jobs to email."

    top = round(jobs[0].match_pct * 100)
    app_url = os.getenv("APP_URL", "http://127.0.0.1:8000")
    body = (
        '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto;">'
        f'<h2 style="margin:0 0 4px;">{len(jobs)} new match{"es" if len(jobs) != 1 else ""} today</h2>'
        '<p style="color:#666;margin:0 0 16px;font-size:13px;">Ranked by how many of the required skills you have.</p>'
        + "".join(_card(j) for j in jobs)
        + f'<p style="margin-top:16px;"><a href="{html.escape(app_url)}" '
          'style="display:inline-block;background:#111;color:#fff;padding:10px 16px;'
          'border-radius:8px;text-decoration:none;font-size:14px;">Open JobHunt</a></p></div>'
    )
    send(f"{len(jobs)} new match{'es' if len(jobs) != 1 else ''} today (top: {top}%) — JobHunt", body)
    for j in jobs:
        j.emailed = True
    db.commit()
    return f"Emailed {len(jobs)} jobs."