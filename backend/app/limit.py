from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException

from .cache import redis_client

LIMITS = {
    "like": (40, 60),
    "comment": (10, 60),
    "upload": (5, 3600),
    "follow": (30, 60),
    "profile": (20, 60),
    "notify": (20, 60),
    "message": (30, 60),
}
_buckets: dict[str, deque] = defaultdict(deque)


def allowed(bucket: str, user_id: int) -> bool:
    limit, window = LIMITS[bucket]
    key = f"{bucket}:{user_id}"
    client = redis_client()
    if client is not None:
        try:
            redis_key = f"rl:{key}"
            count = client.incr(redis_key)
            if count == 1:
                client.expire(redis_key, window)
            return int(count) <= limit
        except Exception:
            pass
    now = time.time()
    events = _buckets[key]
    while events and now - events[0] > window:
        events.popleft()
    if len(events) >= limit:
        return False
    events.append(now)
    return True


def enforce(bucket: str, user_id: int) -> None:
    if not allowed(bucket, user_id):
        raise HTTPException(status_code=429, detail="Аз ҳад зиёд дархост. Каме интизор шавед.")
