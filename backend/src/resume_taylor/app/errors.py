"""Turning the storage layer's exceptions into JSON error responses."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .storage import facts as facts_mod
from .storage import profile_store, resume_ingest
from .storage.projects import NotFound, ProjectError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFound)
    async def _not_found(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ProjectError)
    async def _project_error(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    for exc_type in (profile_store.ProfileError, resume_ingest.IngestError, facts_mod.FactBankError):
        app.add_exception_handler(exc_type, lambda _r, exc: JSONResponse({"detail": str(exc)}, status_code=400))
