import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse

from app import deps, logs

logs.setup()
log = logging.getLogger("app")
app = FastAPI(title="CV Autofill API")


@app.middleware("http")
async def log_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Always our own ID: accepting the caller's would let them write into logs.
    rid = str(uuid.uuid4())
    token = logs.request_id.set(rid)
    start = time.perf_counter()
    status = 500
    try:
        try:
            response = await call_next(request)
        except Exception:
            # Logged here, inside the request, so the record keeps its ID.
            log.exception("unhandled")
            response = PlainTextResponse("Internal Server Error", status_code=500)
        status = response.status_code
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        # The route pattern, never the real path: paths and queries carry data.
        route = getattr(request.scope.get("route"), "path", "unmatched")
        log.info(
            "request",
            extra={
                "method": request.method,
                "route": route,
                "status": status,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
        logs.request_id.reset(token)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


# For the uptime monitor. Render's health check uses /healthz: failing this
# would restart instances over a database blip, which a restart cannot fix.
@app.get("/readyz")
def readyz(response: Response) -> dict[str, str]:
    checks = {"database": deps.database_ok(), "redis": deps.redis_ok()}
    if not all(checks.values()):
        response.status_code = 503
    return {name: "ok" if ok else "down" for name, ok in checks.items()}
