"""Data-folder housekeeping: backup, open in the file manager, shut down."""

import os
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException

from ..context import Ctx
from ..schemas import OpenFolderBody
from ..services.system import open_path
from ..storage.fs import plain_path

router = APIRouter()


@router.post("/api/system/backup")
def backup_data(ctx: Ctx):
    """Zip the user's inputs, projects and settings (never the API key)."""
    import zipfile

    dest = plain_path(ctx.paths.data_root) / f"ResumeTaylor-backup-{datetime.now():%Y-%m-%d-%H-%M-%S}.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for sub in (ctx.paths.input_dir, ctx.paths.projects_dir):
            for f in plain_path(sub).rglob("*"):
                if f.is_file() and "_trash" not in f.parts:
                    z.write(f, f.relative_to(plain_path(ctx.paths.data_root)))
        for f in (ctx.paths.deny_path, ctx.paths.settings_path):
            if f.exists():
                z.write(plain_path(f), f.name)
    open_path(dest.parent)
    return {"path": str(dest)}


@router.post("/api/system/open-folder")
def open_folder(ctx: Ctx, body: OpenFolderBody):
    targets = {"data": ctx.paths.data_root, "inputs": ctx.paths.input_dir, "projects": ctx.paths.projects_dir,
               "archive": ctx.paths.archive_dir}
    if body.target not in targets:
        raise HTTPException(400, "Unknown folder.")
    open_path(targets[body.target])
    return {"ok": True}


@router.post("/api/system/shutdown")
def shutdown():
    def _stop():
        time.sleep(0.5)
        os._exit(0)

    import threading

    threading.Thread(target=_stop, daemon=True).start()
    return {"ok": True}
