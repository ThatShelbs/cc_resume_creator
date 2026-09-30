"""The Resume Taylor HTTP API (FastAPI) plus the built React app.

`create_app()` wires the pieces together: the shared AppContext, the security
middleware (see security.py), error handlers, one router per area under routers/,
and the single-page app fallback last.
"""

import shutil

from fastapi import FastAPI

from .. import __version__
from ..config import DO_NOT_CLAIM_EXAMPLE
from .context import AppContext
from .errors import register_error_handlers
from .routers import demo, facts, imports, maintenance, profile, projects, resume, settings, system
from .routers import jobs as jobs_router
from .security import LOOPBACK_HOSTS, install_security
from .services.jobs import JobManager
from .spa import spa_router
from .storage.paths import Paths
from .storage.projects import ProjectStore


def create_app(paths: Paths, token: str, *, extra_hosts: set | None = None,
               jobs: JobManager | None = None) -> FastAPI:
    paths.ensure()
    if not paths.deny_path.exists() and DO_NOT_CLAIM_EXAMPLE.exists():
        shutil.copy(DO_NOT_CLAIM_EXAMPLE, paths.deny_path)  # starter never-claim list
    store = ProjectStore(paths.projects_dir, paths.trash_dir)
    jobs = jobs or JobManager()
    allowed_hosts = LOOPBACK_HOSTS | (extra_hosts or set())

    app = FastAPI(
        title="Resume Taylor API",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.paths = paths
    app.state.jobs = jobs
    app.state.store = store
    app.state.ctx = AppContext(paths=paths, token=token, store=store, jobs=jobs, allowed_hosts=allowed_hosts)

    install_security(app, token, allowed_hosts)
    register_error_handlers(app)

    # Registration order is the order routes appear in the OpenAPI schema.
    for module in (system, settings, demo, maintenance, profile, resume, facts, projects, imports, jobs_router):
        app.include_router(module.router)
    app.include_router(spa_router(token))  # catch-all: must come last
    return app
