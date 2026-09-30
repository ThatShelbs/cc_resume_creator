"""Evidence: the fact bank and the never-claim list."""

from fastapi import APIRouter, HTTPException

from ..context import AppContext, Ctx
from ..schemas import DraftFactsBody, FactsBody, PhraseBody, TextBody
from ..storage import facts as facts_mod
from ..storage import profile_store

router = APIRouter()


def facts_payload(ctx: AppContext) -> dict:
    items = facts_mod.read_facts(ctx.paths.fact_bank_path)
    comps = ctx.companies()
    return {
        "exists": ctx.paths.fact_bank_path.exists(),
        "facts": [f.model_dump() for f in items],
        "companies": comps,
        "kinds": facts_mod.FACT_KINDS,
        "employer_issues": facts_mod.employer_issues(items, comps),
    }


@router.get("/api/facts")
def get_facts(ctx: Ctx):
    return facts_payload(ctx)


@router.put("/api/facts")
def put_facts(ctx: Ctx, body: FactsBody):
    if ctx.paths.fact_bank_path.exists():
        profile_store.backup(ctx.paths.fact_bank_path, ctx.paths.archive_dir)
    facts_mod.write_facts(ctx.paths.fact_bank_path, body.facts)
    ctx.invalidate_sources()
    return facts_payload(ctx)


@router.post("/api/facts/draft")
def draft_facts(ctx: Ctx, body: DraftFactsBody):
    pp, rp = ctx.require_inputs()
    if ctx.paths.fact_bank_path.exists() and not body.force:
        raise HTTPException(409, "You already have a fact bank. Confirm to replace it (a backup is kept).")
    if ctx.paths.fact_bank_path.exists():
        profile_store.backup(ctx.paths.fact_bank_path, ctx.paths.archive_dir)
    s = ctx.settings()
    args = [*ctx.paths.fact_bank_command, "--profile", str(pp), "--resume", str(rp),
            "--out", str(ctx.paths.fact_bank_path)]
    if body.force:
        args.append("--force")
    try:
        job = ctx.jobs.submit(
            "fact_bank", "Drafting your fact bank", args,
            timeout=s.timeout_seconds * 3 + 60,
            env=ctx.job_env(s),
            on_success=lambda _job: ctx.invalidate_sources(),
        )
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from None
    return job.summary()


@router.get("/api/guardrails")
def get_guardrails(ctx: Ctx):
    text = facts_mod.read_deny_text(ctx.paths.deny_path)
    return {"text": text, "patterns": facts_mod.check_deny_text(text)}


@router.put("/api/guardrails")
def put_guardrails(ctx: Ctx, body: TextBody):
    facts_mod.write_deny_text(ctx.paths.deny_path, body.text)
    ctx.invalidate_sources()
    return get_guardrails(ctx)


@router.post("/api/guardrails/test")
def test_guardrails(body: PhraseBody):
    return {"matches": facts_mod.match_phrase(body.text, body.phrase), "patterns": facts_mod.check_deny_text(body.text)}
