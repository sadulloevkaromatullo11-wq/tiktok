from __future__ import annotations

import logging

from .config import settings

log = logging.getLogger("minitok.cache")
_client = None
_ready = False


def redis_client():
    global _client, _ready
    if _ready:
        return _client
    _ready = True
    if not settings.redis_url:
        return None
    try:
        import redis

        client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.4,
            socket_timeout=0.4,
            decode_responses=True,
        )
        client.ping()
        _client = client
        log.info("Redis пайваст шуд")
    except Exception:
        log.warning("Redis дастнорас аст. Хотираи маҳаллӣ истифода мешавад.")
        _client = None
    return _client
