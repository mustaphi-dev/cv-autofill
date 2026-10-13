from app import deps


def hit(key: str, limit: int, window: int) -> int | None:
    """Counts one use of `key` in a fixed window of `window` seconds. Returns
    None while under `limit`, otherwise the seconds until the window resets."""
    pipe = deps.cache.pipeline()
    pipe.incr(key)
    pipe.expire(key, window, nx=True)
    pipe.ttl(key)
    count, _, ttl = pipe.execute()
    return None if count <= limit else max(ttl, 1)
