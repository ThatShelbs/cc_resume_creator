"""Serving the prebuilt React app (frontend/dist) as a single-page app."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from ..layout import DIST_DIR


def spa_router(token: str) -> APIRouter:
    """Catch-all route for everything that isn't /api. Include it last."""
    router = APIRouter()

    @router.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found.")
        dist = DIST_DIR.resolve()
        if full_path:
            candidate = (dist / full_path).resolve()
            if dist in candidate.parents and candidate.is_file():
                headers = {"Cache-Control": "public, max-age=31536000, immutable"} if "/assets/" in f"/{full_path}" else {}
                return FileResponse(candidate, headers=headers)
        index = dist / "index.html"
        if not index.exists():
            return HTMLResponse(
                "<h1>Resume Taylor</h1><p>The web app hasn't been built yet. Run "
                "<code>Launch Resume Taylor.bat</code> (or <code>npm run build</code> in frontend/).</p>",
                status_code=503,
            )
        html = index.read_text(encoding="utf-8").replace("__TAYLOR_TOKEN__", token)
        return HTMLResponse(html, headers={"Cache-Control": "no-store"})

    return router
