"""Importing job postings left in resume_input/ by the command-line workflow."""

from pathlib import Path

from fastapi import APIRouter

from ...pipeline.sources import JOB_POSTING_EXTS, read_input_text
from ..context import Ctx
from ..schemas import ImportBody
from ..storage.projects import guess_company_role

router = APIRouter()


@router.get("/api/import/candidates")
def import_candidates(ctx: Ctx):
    imported = {m.imported_from for m in ctx.store.all() if m.imported_from}
    if not ctx.paths.input_dir.exists():
        return []
    return [
        {"file": p.name, **guess_company_role(_safe_read(p))}
        for p in sorted(ctx.paths.input_dir.glob("in_job*"))
        if p.suffix.lower() in JOB_POSTING_EXTS and p.name not in imported
    ]


def _safe_read(p: Path) -> str:
    try:
        return read_input_text(p)
    except (Exception, SystemExit):
        return ""


@router.post("/api/import")
def import_postings(ctx: Ctx, body: ImportBody):
    created = []
    for name in body.files:
        p = ctx.paths.input_dir / Path(name).name
        if not p.exists() or not p.name.startswith("in_job"):
            continue
        text = _safe_read(p)
        if len(text.strip()) < 40:
            continue
        guess_ = guess_company_role(text)
        meta = ctx.store.create(job_text=text, company=guess_["company"], role=guess_["role"],
                            template=ctx.settings().default_template, imported_from=p.name)
        created.append(meta.id)
    return {"created": created}
