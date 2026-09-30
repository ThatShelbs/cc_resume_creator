"""Liveness probe and the system status the UI's setup screens read."""

import sys

from fastapi import APIRouter

from ... import __version__
from ...pipeline.render.templates import TEMPLATES
from ..context import Ctx
from ..services import demo
from ..services.system import word_available
from ..storage import credentials
from ..storage import facts as facts_mod
from ..storage.fs import plain_path
from ..storage.projects import STATUSES
from ..storage.settings import EFFORT_CHOICES, MODEL_CHOICES

router = APIRouter()


@router.get("/api/health")
def health():
    return {"app": "resume-taylor", "version": __version__}


@router.get("/api/system")
def system(ctx: Ctx):
    pp, rp = ctx.profile_path(), ctx.resume_path()
    fact_count = None
    if ctx.paths.fact_bank_path.exists():
        try:
            fact_count = len(facts_mod.read_facts(ctx.paths.fact_bank_path))
        except facts_mod.FactBankError:
            fact_count = 0
    deny_count = len([r for r in facts_mod.check_deny_text(facts_mod.read_deny_text(ctx.paths.deny_path)) if not r["error"]])
    return {
        "version": __version__,
        "claude": {**ctx.claude.info(), **ctx.claude.login()},
        "api_key": credentials.status(ctx.paths.secrets_path),
        "sample_loaded": demo.is_loaded(ctx.paths),
        "word": word_available(),
        "platform": sys.platform,
        "data_root": str(plain_path(ctx.paths.data_root)),
        "inputs": {
            "profile": pp.name if pp else None,
            "resume": rp.name if rp else None,
            "fact_bank": fact_count,
            "deny_patterns": deny_count,
        },
        "onboarding_needed": not (pp and rp),
        "templates": [
            {"key": t.key, "label": t.label, "description": t.description} for t in TEMPLATES.values()
        ],
        "statuses": STATUSES,
        "models": MODEL_CHOICES,
        "efforts": EFFORT_CHOICES,
        "active_jobs": [j.summary() for j in ctx.jobs.active()],
    }
