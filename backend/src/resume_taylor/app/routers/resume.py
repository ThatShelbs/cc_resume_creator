"""The base resume: upload, review, confirm, download."""

import json
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ...pipeline.parsing import parse_applicant_info
from ...pipeline.sources import docx_paras
from ..context import Ctx
from ..schemas import ResumeConfirm
from ..services.jobs import Job
from ..storage import facts as facts_mod
from ..storage import profile_store, resume_ingest
from ..uploads import read_upload

router = APIRouter()


@router.get("/api/resume")
def get_resume(ctx: Ctx):
    path = ctx.resume_path()
    if not path:
        return {"exists": False, "file": None, "updated": None, "structure": None, "originals": []}
    structure = resume_ingest.structure_from_paras(docx_paras(path, strip=False))
    structure.source = "current"
    structure.source_file = path.name
    originals = sorted((p.name for p in ctx.paths.originals_dir.glob("*") if p.is_file()), reverse=True) \
        if ctx.paths.originals_dir.exists() else []
    return {
        "exists": True,
        "file": path.name,
        "updated": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "structure": structure.model_dump(exclude={"raw_text"}),
        "originals": originals[:10],
    }


@router.post("/api/resume/upload")
async def upload_resume(ctx: Ctx, file: UploadFile = File(...)):
    name, data = await read_upload(file, (".pdf", ".docx"))
    ctx.paths.originals_dir.mkdir(parents=True, exist_ok=True)
    uploaded_at = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    saved = ctx.paths.originals_dir / f"{uploaded_at}_{name}"
    saved.write_bytes(data)
    try:
        structure = resume_ingest.ingest(saved)
    except resume_ingest.IngestError:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Couldn't read that file ({exc}).") from None
    upload_id = uuid.uuid4().hex[:12]
    ctx.uploads[upload_id] = {"path": saved}
    return {
        "upload_id": upload_id,
        "structure": structure.model_dump(exclude={"raw_text"}),
        "needs_ai": not structure.jobs,
        "prefill": resume_ingest.prefill_contact(structure),
    }


@router.post("/api/resume/ai/{upload_id}")
def structure_with_ai(ctx: Ctx, upload_id: str):
    upload = ctx.uploads.get(upload_id)
    if not upload:
        raise HTTPException(404, "Upload the file again.")
    out = ctx.paths.scratch_dir / f"structure_{upload_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    def on_success(job: Job) -> None:
        structure = resume_ingest.ResumeStructure(**json.loads(out.read_text(encoding="utf-8")))
        job.result = {
            "structure": structure.model_dump(exclude={"raw_text"}),
            "prefill": resume_ingest.prefill_contact(structure),
        }
        out.unlink(missing_ok=True)

    s = ctx.settings()
    job = ctx.jobs.submit(
        "ingest", "Structuring your resume with Claude",
        ["-m", "resume_taylor.app.storage.resume_ingest", "--ai", str(upload["path"]), "--out", str(out)],
        timeout=s.timeout_seconds * 2 + 60,
        env=ctx.job_env(s),
        on_success=on_success,
    )
    return job.summary()


@router.post("/api/resume/confirm")
def confirm_resume(ctx: Ctx, body: ResumeConfirm):
    resume_ingest.validate_structure(body.structure)
    existing = ctx.resume_path()
    contact = None
    pp = ctx.profile_path()
    if pp:
        try:
            contact = parse_applicant_info(pp)
        except SystemExit:
            contact = None
    if contact:
        suffix = f"{contact['first_name']}-{contact['last_name']}".strip("-")
    else:  # no profile yet (onboarding uploads the resume first): use the resume's header
        suffix = resume_ingest.prefill_contact(body.structure)["name"].replace(" ", "-") or "base"
    suffix = re.sub(r"[^\w-]+", "-", suffix).strip("-") or "base"
    target = ctx.paths.input_dir / f"in_resume_{suffix}.docx"
    if existing:
        profile_store.backup(existing, ctx.paths.archive_dir)
        if existing != target:
            existing.unlink()
    resume_ingest.write_resume_docx(body.structure, target)
    ctx.invalidate_sources()
    comps = [j.company for j in body.structure.jobs]
    issues = facts_mod.employer_issues(facts_mod.read_facts(ctx.paths.fact_bank_path), comps) \
        if ctx.paths.fact_bank_path.exists() else []
    return {"file": target.name, "fact_bank_issues": issues}


@router.get("/api/resume/download")
def download_resume(ctx: Ctx):
    path = ctx.resume_path()
    if not path:
        raise HTTPException(404, "No base resume yet.")
    return FileResponse(path, filename=path.name)
