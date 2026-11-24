from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User, utc_now

log = logging.getLogger("minitok.auth")
MAX_AGE = 60 * 60 * 24


def verify_init_data(init_data: str, bot_token: str, now: float | None = None) -> dict:
    if not bot_token:
        raise ValueError("missing token")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received = pairs.pop("hash", "")
    if not received:
        raise ValueError("missing hash")
    check = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if len(calculated) != len(received) or not hmac.compare_digest(calculated, received):
        raise ValueError("bad hash")
    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except ValueError as exc:
        raise ValueError("bad auth_date") from exc
    current = time.time() if now is None else now
    if auth_date > current + 60 or current - auth_date > MAX_AGE:
        raise ValueError("expired")
    try:
        user = json.loads(pairs.get("user") or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("bad user") from exc
    if not isinstance(user, dict) or "id" not in user:
        raise ValueError("bad user")
    return user


def _session_user_id(init_data: str) -> int | None:
    from .cache import redis_client

    client = redis_client()
    if client is None:
        return None
    token = hashlib.sha256(init_data.encode()).hexdigest()
    try:
        raw = client.get(f"sess:{token}")
    except Exception:
        return None
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _store_session(init_data: str, user_id: int) -> None:
    from .cache import redis_client

    client = redis_client()
    if client is None:
        return
    token = hashlib.sha256(init_data.encode()).hexdigest()
    try:
        client.setex(f"sess:{token}", MAX_AGE, str(user_id))
    except Exception:
        log.warning("Сессия дар Redis сабт нашуд", exc_info=True)


def upsert_telegram_user(db: Session, payload: dict) -> User:
    user_id = int(payload["id"])
    user = db.get(User, user_id)
    first = (payload.get("first_name") or "Корбар")[:128]
    last = (payload.get("last_name") or None)
    username = (payload.get("username") or None)
    photo = payload.get("photo_url") or None
    if user is None:
        user = User(
            id=user_id,
            username=username,
            first_name=first,
            last_name=last,
            photo_url=photo,
            bio="",
            links="",
            is_demo=False,
            created_at=utc_now(),
        )
        db.add(user)
    else:
        user.username = username
        user.first_name = first
        user.last_name = last
        if photo:
            user.photo_url = photo
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or " " not in authorization.strip():
        raise HTTPException(status_code=401, detail="Авторизатсия лозим аст.")
    scheme, param = authorization.strip().split(" ", 1)
    scheme = scheme.lower()
    if scheme == "tma":
        cached = _session_user_id(param)
        if cached is not None:
            user = db.get(User, cached)
            if user is not None:
                return user
        try:
            payload = verify_init_data(param, settings.bot_token)
        except ValueError as exc:
            log.info("initData рад шуд: %s", exc)
            if str(exc) == "missing token":
                raise HTTPException(status_code=401, detail="BOT_TOKEN танзим нашудааст.") from exc
            raise HTTPException(status_code=401, detail="initData нодуруст аст.") from exc
        user = upsert_telegram_user(db, payload)
        _store_session(param, user.id)
        return user
    if scheme == "demo":
        if not settings.allow_demo:
            raise HTTPException(status_code=401, detail="Реҷаи намоиш хомӯш аст.")
        try:
            user_id = int(param)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Корбари намоишӣ нодуруст аст.") from exc
        user = db.get(User, user_id)
        if user is None or not user.is_demo:
            raise HTTPException(status_code=401, detail="Корбари намоишӣ ёфт нашуд.")
        return user
    raise HTTPException(status_code=401, detail="Авторизатсия нодуруст аст.")
