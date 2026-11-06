import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# به‌صورت پیش‌فرض همان دیتابیس Django توسعه
_default_db = Path(__file__).resolve().parent.parent / "backend" / "db.sqlite3"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_default_db}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()