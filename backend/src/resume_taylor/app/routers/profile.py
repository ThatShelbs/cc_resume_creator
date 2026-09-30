"""The applicant profile (in_profile.docx)."""

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..context import Ctx
from ..storage import profile_store
from ..uploads import read_upload

router = APIRouter()


def profile_payload(path: Path | None, backup: Path | None = None) -> dict:
    if not path:
        return {"exists": False, "file": None, "updated": None, "profile": profile_store.Profile().model_dump()}
    return {
        "exists": True,
        "file": path.name,
        "updated": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "profile": profile_store.read_profile(path).model_dump(),
        "backup": backup.name if backup else None,
    }


@router.get("/api/profile")
def get_profile(ctx: Ctx):
    return profile_payload(ctx.profile_path())


@router.put("/api/profile")
def put_profile(ctx: Ctx, body: profile_store.Profile):
    path = ctx.profile_path() or ctx.paths.input_dir / "in_profile.docx"
    backup = profile_store.save_profile(body, path, ctx.paths.archive_dir)
    ctx.invalidate_sources()
    return profile_payload(path, backup)


@router.post("/api/profile/import")
async def import_profile(ctx: Ctx, file: UploadFile = File(...)):
    name, data = await read_upload(file, (".docx",))
    tmp = ctx.paths.scratch_dir / f"{uuid.uuid4().hex}_{name}"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)
    try:
        return {"profile": profile_store.read_profile(tmp).model_dump()}
    except Exception as exc:  # python-docx raises several types on bad files
        raise HTTPException(400, f"Couldn't read that Word file ({exc}).") from None
    finally:
        tmp.unlink(missing_ok=True)


@router.get("/api/profile/download")
def download_profile(ctx: Ctx):
    path = ctx.profile_path()
    if not path:
        raise HTTPException(404, "No profile yet.")
    return FileResponse(path, filename=path.name)
