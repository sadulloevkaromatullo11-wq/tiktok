from __future__ import annotations

import asyncio
import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .bot import bot_loop
from .config import settings
from .db import SessionLocal, init_db
from .media import executor
from .routers import users, videos
from .seed import seed

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("minitok")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    stop = asyncio.Event()
    task = asyncio.create_task(bot_loop(stop))
    log.info("Mini TikTok омода аст. demo=%s db=%s", settings.allow_demo, settings.database_url.split("://", 1)[0])
    yield
    stop.set()
    task.cancel()
    executor.shutdown(wait=False, cancel_futures=True)


app = FastAPI(title="Telegram Mini TikTok", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(users.router)
app.include_router(videos.router)
settings.var_dir.mkdir(parents=True, exist_ok=True)
settings.media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(settings.media_dir)), name="media")


@app.get("/api/health")
def health():
    from .cache import redis_client

    return {
        "ok": True,
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "storage": "s3" if settings.use_s3 else "local",
        "database": "postgres" if settings.database_url.startswith("postgresql") else "sqlite",
        "redis": redis_client() is not None,
        "demo": settings.allow_demo,
    }


@app.get("/api/config")
def public_config():
    return {
        "bot_username": settings.bot_username,
        "demo": settings.allow_demo,
    }


_dist = settings.root / "frontend" / "dist"


@app.get("/")
@app.get("/{path:path}")
def spa(path: str = ""):
    if path.startswith("api") or path.startswith("media"):
        raise HTTPException(status_code=404, detail="Ёфт нашуд.")
    if not _dist.exists():
        raise HTTPException(status_code=404, detail="Фронтенд ҳанӯз ҷамъ нашудааст.")
    target = (_dist / path).resolve() if path else _dist / "index.html"
    try:
        target.relative_to(_dist.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Ёфт нашуд.") from exc
    if target.is_file():
        return FileResponse(target)
    index = _dist / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Ёфт нашуд.")
