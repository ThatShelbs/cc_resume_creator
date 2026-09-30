"""Security model for a local-only app: the server binds to 127.0.0.1, rejects any
request whose Host isn't a loopback name (defeats DNS rebinding), and requires a
random per-launch token on every /api call (injected into the served index.html,
sent back as X-Taylor-Token, or as ?t= for plain links like downloads). A web page
in another tab can't read the token, so it can't drive the API."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}
# Reachable without the session token: a liveness probe for the launcher and
# the API docs (schema only, no data).
OPEN_PATHS = {"/api/health", "/api/docs", "/api/openapi.json"}


def _hostname(host_header: str) -> str:
    host = host_header.strip().lower()
    if host.startswith("["):
        return host[: host.find("]") + 1]
    return host.rsplit(":", 1)[0] if ":" in host else host


def install_security(app: FastAPI, token: str, allowed_hosts: set) -> None:
    @app.middleware("http")
    async def guard(request: Request, call_next):
        if _hostname(request.headers.get("host", "")) not in allowed_hosts:
            return JSONResponse({"detail": "Resume Taylor only answers on localhost."}, status_code=421)
        path = request.url.path
        if path.startswith("/api/") and path not in OPEN_PATHS:
            supplied = request.headers.get("x-taylor-token") or request.query_params.get("t")
            if supplied != token:
                return JSONResponse({"detail": "Missing or invalid session token. Reload the page."}, status_code=403)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response
