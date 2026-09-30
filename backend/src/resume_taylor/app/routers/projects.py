"""Job-application projects: content, generation, versions, files, trash."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from ...pipeline.render.templates import TEMPLATES
from ...pipeline.sources import read_input_text
from ..context import Ctx
from ..schemas import NewProject, ProjectPatch, RenderBody, TextBody
from ..services import lint as lint_mod
from ..services.system import open_path
from ..storage import facts as facts_mod
from ..storage.projects import guess_company_role
from ..uploads import read_upload

router = APIRouter()


@router.get("/api/projects")
def list_projects(ctx: Ctx):
    hashes = ctx.current_hashes()
    return [ctx.project_summary(m, hashes) for m in ctx.store.all()]


@router.post("/api/projects/guess")
def guess(body: TextBody):
    return guess_company_role(body.text)


@router.post("/api/projects/extract-posting")
async def extract_posting(ctx: Ctx, file: UploadFile = File(...)):
    name, data = await read_upload(file, (".docx", ".pdf", ".txt", ".md"))
    tmp = ctx.paths.scratch_dir / f"{uuid.uuid4().hex}_{name}"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)
    try:
        text = read_input_text(tmp)
    except (Exception, SystemExit) as exc:
        raise HTTPException(400, f"Couldn't read text from that file ({exc}).") from None
    finally:
        tmp.unlink(missing_ok=True)
    if not text.strip():
        raise HTTPException(400, "No text could be read from that file (a scanned PDF?). Paste the text instead.")
    return {"text": text, **guess_company_role(text)}


@router.post("/api/projects")
def create_project(ctx: Ctx, body: NewProject):
    s = ctx.settings()
    meta = ctx.store.create(
        job_text=body.job_text,
        company=body.company,
        role=body.role,
        name=body.name,
        url=body.url,
        template=body.template or s.default_template,
        cover_letter=s.cover_letter_default if body.cover_letter is None else body.cover_letter,
    )
    job = ctx.start_pipeline(meta.id, render=False).summary() if body.generate else None
    return {"project": ctx.project_summary(ctx.store.get(meta.id), ctx.current_hashes()), "job": job}


@router.get("/api/projects/{pid}")
def get_project(ctx: Ctx, pid: str):
    meta = ctx.store.get(pid)
    job = ctx.jobs.latest_for(pid)
    return {
        "project": ctx.project_summary(meta, ctx.current_hashes()),
        "job_text": ctx.store.get_job_text(pid),
        "result": ctx.store.get_result(pid),
        "outputs": ctx.store.outputs(pid),
        "job": job.summary() if job else None,
    }


@router.patch("/api/projects/{pid}")
def patch_project(ctx: Ctx, pid: str, body: ProjectPatch):
    patch = body.model_dump(exclude_unset=True)
    meta = ctx.store.update(pid, patch)
    return ctx.project_summary(meta, ctx.current_hashes())


@router.put("/api/projects/{pid}/job")
def put_job_text(ctx: Ctx, pid: str, body: TextBody):
    ctx.store.get(pid)
    ctx.store.set_job_text(pid, body.text)
    return ctx.project_summary(ctx.store.touch(pid), ctx.current_hashes())


@router.put("/api/projects/{pid}/result")
def put_result(ctx: Ctx, pid: str, result: dict = Body(...)):
    meta = ctx.store.save_result(pid, result)
    return ctx.project_summary(meta, ctx.current_hashes())


@router.post("/api/projects/{pid}/lint")
def lint_project(ctx: Ctx, pid: str, result: dict = Body(...)):
    ctx.store.get(pid)
    sources = ctx.source_context()
    return lint_mod.lint_result(result, sources["source_text"], sources["fact_bank"], sources["deny"])


@router.get("/api/projects/{pid}/facts")
def project_facts(ctx: Ctx, pid: str):
    """Fact text for citation hover cards."""
    ctx.store.get(pid)
    return {f.id: {"text": f.text, "employer": f.employer, "kind": f.kind}
            for f in facts_mod.read_facts(ctx.paths.fact_bank_path)}


@router.post("/api/projects/{pid}/generate")
def generate(ctx: Ctx, pid: str):
    return ctx.start_pipeline(pid, render=False).summary()


@router.post("/api/projects/{pid}/render")
def render(ctx: Ctx, pid: str, body: RenderBody | None = None):
    if body and body.template:
        ctx.store.update(pid, {"template": body.template})
    return ctx.start_pipeline(pid, render=True).summary()


@router.get("/api/projects/{pid}/versions")
def versions(ctx: Ctx, pid: str):
    return ctx.store.versions(pid)


@router.get("/api/projects/{pid}/versions/{vid}")
def version(ctx: Ctx, pid: str, vid: str):
    return ctx.store.version_result(pid, vid)


@router.post("/api/projects/{pid}/versions/{vid}/restore")
def restore_version(ctx: Ctx, pid: str, vid: str):
    restored = ctx.store.version_result(pid, vid)
    ctx.store.rotate(pid)
    ctx.store.save_result(pid, restored)
    if restored.get("template") in TEMPLATES:
        ctx.store.update(pid, {"template": restored["template"]})
    return ctx.start_pipeline(pid, render=True).summary()


def file_response(path: Path, download: bool) -> FileResponse:
    media = {".pdf": "application/pdf", ".md": "text/markdown; charset=utf-8",
             ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    return FileResponse(
        path,
        media_type=media.get(path.suffix.lower(), "application/octet-stream"),
        filename=path.name if download else None,
        content_disposition_type="attachment" if download else "inline",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/projects/{pid}/files/{name}")
def project_file(ctx: Ctx, pid: str, name: str, download: bool = False):
    return file_response(ctx.store.safe_file(pid, "outputs", name), download)


@router.get("/api/projects/{pid}/versions/{vid}/files/{name}")
def version_file(ctx: Ctx, pid: str, vid: str, name: str, download: bool = True):
    return file_response(ctx.store.safe_file(pid, "versions", vid, name), download)


@router.get("/api/projects/{pid}/report")
def report(ctx: Ctx, pid: str):
    for f in ctx.store.outputs(pid):
        if f["name"].startswith("out_resume_") and f["name"].endswith("_report.md"):
            return PlainTextResponse(ctx.store.safe_file(pid, "outputs", f["name"]).read_text(encoding="utf-8"))
    raise HTTPException(404, "No report yet.")


@router.get("/api/projects/{pid}/log")
def run_log(ctx: Ctx, pid: str):
    p = ctx.store.dir(pid) / "run.log"
    return PlainTextResponse(p.read_text(encoding="utf-8") if p.exists() else "")


@router.post("/api/projects/{pid}/duplicate")
def duplicate(ctx: Ctx, pid: str):
    return ctx.project_summary(ctx.store.duplicate(pid), ctx.current_hashes())


@router.delete("/api/projects/{pid}")
def delete_project(ctx: Ctx, pid: str):
    job = ctx.jobs.latest_for(pid)
    if job and not job.done:
        raise HTTPException(409, "Wait for the running job to finish (or cancel it) before deleting.")
    return {"trash_id": ctx.store.trash_project(pid)}


@router.post("/api/projects/{pid}/open-folder")
def open_project_folder(ctx: Ctx, pid: str):
    open_path(ctx.store.dir(pid))
    return {"ok": True}


@router.get("/api/trash")
def trash(ctx: Ctx):
    return ctx.store.list_trash()


@router.post("/api/trash/{tid}/restore")
def restore(ctx: Ctx, tid: str):
    return ctx.project_summary(ctx.store.restore(tid), ctx.current_hashes())
