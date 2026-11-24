from __future__ import annotations

import logging

try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

import httpx

from .config import settings
from .limit import allowed
from .media import executor
from .models import User, Video

log = logging.getLogger("minitok.notify")


def _deliver(chat_id: int, text: str, video_id: str | None) -> None:
    if not settings.bot_token or not allowed("notify", chat_id):
        return
    payload: dict = {"chat_id": chat_id, "text": text}
    if video_id and settings.webapp_url.startswith("https://"):
        joiner = "&" if "?" in settings.webapp_url else "?"
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": "Кушодани видео", "web_app": {"url": f"{settings.webapp_url}{joiner}v={video_id}"}}]
            ]
        }
    try:
        httpx.post(
            f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
            json=payload,
            timeout=8,
        )
    except Exception:
        log.warning("Огоҳинома фиристода нашуд", exc_info=True)


def notify(owner_id: int, actor: User, video: Video, kind: str, text: str = "") -> None:
    if not settings.bot_token or owner_id == actor.id:
        return
    name = actor.first_name or actor.username or "Касе"
    if kind == "like":
        body = f"❤️ {name} ба видеои шумо лайк гузошт"
    else:
        preview = text.replace("\n", " ").strip()[:120]
        body = f"💬 {name}: {preview}"
    executor.submit(_deliver, owner_id, body, video.id)
