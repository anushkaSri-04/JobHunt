import os
from dotenv import load_dotenv
load_dotenv()  # reads .env so DATABASE_URL and SESSION_SECRET are set on Windows too
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///jobhunt.db")

if DATABASE_URL.startswith("sqlite"):
    # FastAPI runs sync routes in a thread pool; SQLite must allow that
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as db:
        yield db