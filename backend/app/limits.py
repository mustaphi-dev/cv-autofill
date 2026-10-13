from fastapi import HTTPException

from app import deps


def hit(key: str, limit: int, window: int, message: str) -> None:
    """Counts one use of `key` in a fixed window of `window` seconds. Over
    `limit`, raises 429 with the seconds until the window resets."""
    pipe = deps.cache.pipeline()
    pipe.incr(key)
    pipe.expire(key, window, nx=True)
    pipe.ttl(key)
    count, _, ttl = pipe.execute()
    if count > limit:
        raise HTTPException(429, message, {"Retry-After": str(max(ttl, 1))})
