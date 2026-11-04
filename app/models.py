from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

now = lambda: datetime.now(timezone.utc)


class AppUser(Base):
    __tablename__ = "app_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))


class Company(Base):
    __tablename__ = "company"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    ats: Mapped[str] = mapped_column(String(20))
    slug: Mapped[str] = mapped_column(String(120))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_status: Mapped[str | None] = mapped_column(String(60))
    last_job_count: Mapped[int] = mapped_column(Integer, default=0)
    zero_days: Mapped[int] = mapped_column(Integer, default=0)  # slug-health signal


class Job(Base):
    __tablename__ = "job"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # ats:slug:ext_id
    company_id: Mapped[int | None] = mapped_column(ForeignKey("company.id"))
    company_name: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(300))
    location: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(600), default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new|applied|skipped
    emailed: Mapped[bool] = mapped_column(Boolean, default=False)
    match_pct: Mapped[float | None] = mapped_column(Float)      # 0..1, None = no known skills found
    min_years: Mapped[int | None] = mapped_column(Integer)      # smallest "N years" in the posting
    skills: Mapped[dict | None] = mapped_column(JSON)           # req/nice x matched/missing


class Run(Base):
    __tablename__ = "run"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trigger: Mapped[str] = mapped_column(String(20), default="manual")
    mock: Mapped[bool] = mapped_column(Boolean, default=False)
    counts: Mapped[dict] = mapped_column(JSON, default=dict)  # fetched / kept / new
    log: Mapped[str] = mapped_column(Text, default="")


class ProfileSkill(Base):
    __tablename__ = "profile_skill"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)   # canonical name from skills.yaml