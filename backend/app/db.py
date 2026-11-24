from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from .config import settings
from .models import Base

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
pool = NullPool if settings.database_url.startswith("sqlite") else None
engine_kwargs = {"connect_args": connect_args}
if pool is not None:
    engine_kwargs["poolclass"] = pool
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 2

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    settings.var_dir.mkdir(parents=True, exist_ok=True)
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    (settings.media_dir / "original").mkdir(exist_ok=True)
    (settings.media_dir / "ready").mkdir(exist_ok=True)
    (settings.media_dir / "thumbs").mkdir(exist_ok=True)
    (settings.media_dir / "hls").mkdir(exist_ok=True)
    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
