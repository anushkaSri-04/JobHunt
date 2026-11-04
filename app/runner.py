"""One pipeline run: fetch -> prefilter -> dedupe -> match skills -> store."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlalchemy import select

from engine.fetch import fetch_board
from engine.mock import fetch_all_mock
from engine.prefilter import prefilter, _parse_date
from engine.skills import analyze, find_skills
from . import models as m

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def seed_companies(db) -> int:
    """Import companies.yaml once, if the table is empty."""
    if db.scalar(select(m.Company.id).limit(1)):
        return 0
    rows = yaml.safe_load((ROOT / "companies.yaml").read_text())["companies"]
    db.add_all(m.Company(name=r["name"], ats=r["ats"], slug=r["slug"]) for r in rows)
    db.commit()
    return len(rows)


# ---- profile skills --------------------------------------------------------
def profile_skills(db) -> set[str]:
    return set(db.scalars(select(m.ProfileSkill.name)))


def seed_profile(db, path: Path | None = None) -> tuple[set[str], list[str]]:
    """Fill profile_skill from profile.json. Returns (skills_found, core_skills_not_in_dictionary)."""
    data = json.loads((path or ROOT / "profile.json").read_text(encoding="utf-8"))
    core = [s for s in data.get("core_skills", []) if s]
    texts = core + [data.get("experience", "")] + list(data.get("notable_projects", []))
    found = set().union(*(find_skills(t) for t in texts if t))
    unknown = [s for s in core if not find_skills(s)]
    have = profile_skills(db)
    db.add_all(m.ProfileSkill(name=n) for n in sorted(found - have))
    db.commit()
    return found, unknown


# ---- matching --------------------------------------------------------------
def apply_match(job: m.Job, profile: set[str]) -> None:
    a = analyze(job.description, profile)
    job.match_pct, job.min_years, job.skills = a["pct"], a["min_years"], a["skills"]


def rematch_all(db) -> int:
    """Recompute every job's match. Run after the profile or the dictionary changes."""
    profile = profile_skills(db)
    jobs = db.scalars(select(m.Job)).all()
    for j in jobs:
        apply_match(j, profile)
    db.commit()
    return len(jobs)


# ---- the run ---------------------------------------------------------------
def run_pipeline(db, mock: bool = False, trigger: str = "manual") -> m.Run:
    cfg = load_config()
    profile = profile_skills(db)
    run = m.Run(trigger=trigger, mock=mock)
    db.add(run); db.flush()
    log, fetched = [], []
    if not profile:
        log.append("WARNING: profile has no skills; run `python manage.py profile seed`")

    if mock:
        fetched = fetch_all_mock()
        log.append(f"mock: {len(fetched)} postings")
    else:
        for c in db.scalars(select(m.Company).where(m.Company.enabled)):
            jobs = fetch_board(c.ats, c.slug, c.name)  # never raises; HTTP errors print to console
            c.last_status, c.last_job_count = ("ok" if jobs else "0 jobs"), len(jobs)
            c.zero_days = c.zero_days + 1 if not jobs else 0
            log.append(f"{c.ats}:{c.slug} -> {len(jobs)} jobs")
            fetched += jobs
            time.sleep(0.25)

    kept = prefilter(fetched, cfg["filters"])
    known = set(db.scalars(select(m.Job.id).where(m.Job.id.in_([j.job_id for j in kept]))))
    new = [j for j in kept if j.job_id not in known]
    threshold = float(cfg.get("skill_match_threshold", 0.5))
    shown = 0
    for j in new:
        row = m.Job(id=j.job_id, company_name=j.company, title=j.title, location=j.location,
                    description=j.description, url=j.url, posted_at=_parse_date(j.posted_at))
        apply_match(row, profile)
        shown += row.match_pct is None or row.match_pct >= threshold
        db.add(row)
    run.counts = {"fetched": len(fetched), "kept": len(kept), "new": len(new), "matched": shown}
    run.log = "\n".join(log)
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    return run