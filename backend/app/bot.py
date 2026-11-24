from __future__ import annotations

import asyncio
import logging

try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

import httpx

from .config import settings

log = logging.getLogger("minitok.bot")


def _app_url(start_param: str = "") -> str:
    url = settings.webapp_url
    if not url.startswith("https://"):
        return ""
    if start_param.startswith("v_"):
        joiner = "&" if "?" in url else "?"
        return f"{url}{joiner}v={start_param[2:]}"
    return url


def _keyboard(url: str) -> dict | None:
    if not url:
        return None
    return {"inline_keyboard": [[{"text": "Open App", "web_app": {"url": url}}]]}


async def _setup(client: httpx.AsyncClient, api: str) -> None:
    await client.post(
        f"{api}/setMyCommands",
        json={"commands": [{"command": "start", "description": "Кушодани Mini TikTok"}]},
    )
    url = _app_url()
    if not url:
        return
    await client.post(
        f"{api}/setChatMenuButton",
        json={"menu_button": {"type": "web_app", "text": "Open App", "web_app": {"url": url}}},
    )


async def _handle(client: httpx.AsyncClient, api: str, update: dict) -> None:
    message = update.get("message") or {}
    text = message.get("text") or ""
    chat = message.get("chat") or {}
    if not text.startswith("/start") or "id" not in chat:
        return
    param = text.split(maxsplit=1)[1] if " " in text else ""
    payload = {
        "chat_id": chat["id"],
        "text": "Салом! Видеоҳои кӯтоҳро тамошо кунед, шарҳ диҳед ва видеои худро бор кунед.",
    }
    keyboard = _keyboard(_app_url(param))
    if keyboard:
        payload["reply_markup"] = keyboard
    await client.post(f"{api}/sendMessage", json=payload)


async def bot_loop(stop: asyncio.Event) -> None:
    if not settings.bot_token or not settings.bot_polling:
        return
    api = f"https://api.telegram.org/bot{settings.bot_token}"
    offset = 0
    async with httpx.AsyncClient(timeout=40) as client:
        try:
            await _setup(client, api)
        except Exception:
            log.warning("Танзими бот ноком шуд", exc_info=True)
        while not stop.is_set():
            try:
                response = await client.get(f"{api}/getUpdates", params={"timeout": 25, "offset": offset})
                data = response.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    await _handle(client, api, update)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.warning("getUpdates ноком шуд", exc_info=True)
                await asyncio.sleep(2)
