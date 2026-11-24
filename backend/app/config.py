from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
VAR = ROOT / "backend" / "var"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_db(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    if not url.startswith("postgresql"):
        return url
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "channel_binding"]
    host = (parts.hostname or "").lower()
    if host not in {"", "localhost", "127.0.0.1"} and not any(key == "sslmode" for key, _ in query):
        query.append(("sslmode", "require"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _public_base() -> str:
    explicit = os.environ.get("PUBLIC_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").split(",")[0].strip()
    if domain:
        return "https://" + domain
    return ""


@dataclass(frozen=True)
class Settings:
    root: Path
    var_dir: Path
    media_dir: Path
    database_url: str
    public_url: str
    redis_url: str
    bot_token: str
    bot_username: str
    bot_polling: bool
    webapp_url: str
    allow_demo: bool
    storage: str
    s3_endpoint: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    s3_public_url: str
    s3_region: str
    max_upload_bytes: int = 50 * 1024 * 1024
    min_duration: float = 5.0
    max_duration: float = 60.0

    @property
    def use_s3(self) -> bool:
        return self.storage == "s3" and bool(self.s3_bucket and self.s3_access_key and self.s3_secret_key)


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    bot_token = os.environ.get("BOT_TOKEN", "").strip()
    var_dir = Path(os.environ.get("VAR_DIR", VAR))
    media_dir = Path(os.environ.get("MEDIA_DIR", var_dir / "media"))
    db_default = "sqlite:///" + (var_dir / "app.db").as_posix()
    database_url = _normalize_db(os.environ.get("DATABASE_URL", "").strip() or db_default)
    return Settings(
        root=ROOT,
        var_dir=var_dir,
        media_dir=media_dir,
        database_url=database_url,
        public_url=_public_base(),
        redis_url=os.environ.get("REDIS_URL", "").strip(),
        bot_token=bot_token,
        bot_username=os.environ.get("BOT_USERNAME", os.environ.get("VITE_BOT_USERNAME", "")).strip().lstrip("@"),
        bot_polling=_flag("BOT_POLLING", True),
        webapp_url=os.environ.get("WEBAPP_URL", "").strip().rstrip("/"),
        allow_demo=_flag("DEV_ALLOW_DEMO", not bool(bot_token)),
        storage=os.environ.get("STORAGE", "local").strip().lower() or "local",
        s3_endpoint=os.environ.get("S3_ENDPOINT", "").strip(),
        s3_bucket=os.environ.get("S3_BUCKET", "").strip(),
        s3_access_key=os.environ.get("S3_ACCESS_KEY", "").strip(),
        s3_secret_key=os.environ.get("S3_SECRET_KEY", "").strip(),
        s3_public_url=os.environ.get("S3_PUBLIC_URL", "").strip().rstrip("/"),
        s3_region=os.environ.get("S3_REGION", "auto").strip() or "auto",
    )


settings = load_settings()


def media_url(value: str | None) -> str | None:
    if not value or not value.startswith("/") or not settings.public_url:
        return value
    return settings.public_url + value
