"""The LLM calls: a free-form drafting call plus a narrow JSON-transcription call,
producing only the parts that need judgment: the summary, per-employer bullets, skills."""

import json
import re
import sys

from ..claude_cli import find_claude_cli, invoke_claude, strip_code_fence
from .factbank import format_fact_bank
from .prompts import CITATION_CONTRACT, FORMAT_SYSTEM_PROMPT, PIPELINE_OUTPUT_CONTRACT, load_tailoring_rules
from .runtime import stage
from .skills import extract_skills_from_draft


def _flatten_skills(value) -> list:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        flat = []
        for group in value.values():
            flat.extend(_flatten_skills(group))
        return flat
    return []


def _try_parse_format_json(raw: str, companies: list) -> dict | None:
    match = re.search(r"<RESUME_JSON>(.*?)</RESUME_JSON>", raw, re.DOTALL)
    text = strip_code_fence(match.group(1) if match else raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None

    summary = ""
    for key in ("summary", "professional_summary", "resume_summary"):
        if parsed.get(key):
            summary = parsed[key]
            break

    raw_bullets = parsed.get("bullets_by_company") or {}
    # Match case/whitespace-insensitively since the model copies company
    # names back rather than using a fixed schema.
    normalized = {re.sub(r"\s+", " ", k.strip().lower()): v for k, v in raw_bullets.items()}
    bullets_by_company = {}
    for company in companies:
        key = re.sub(r"\s+", " ", company.strip().lower())
        bullets_by_company[company] = list(normalized.get(key) or [])

    skills = []
    for key in ("skills", "core_skills", "skill_list"):
        if parsed.get(key):
            skills = _flatten_skills(parsed[key])
            break

    return {"summary": summary, "bullets_by_company": bullets_by_company, "skills": skills}


def tailor_content(
    profile_text: str,
    resume_text: str,
    job_text: str,
    jobs: list,
    deny_patterns: list,
    fact_bank: dict | None = None,
    model: str | None = None,
    effort: str | None = None,
) -> dict:
    claude_bin = find_claude_cli()
    companies = [job["company"] for job in jobs]
    company_block = "\n".join(companies)
    contract = PIPELINE_OUTPUT_CONTRACT.replace("{company_block}", company_block)
    if fact_bank:
        contract += CITATION_CONTRACT
    draft_system_prompt = load_tailoring_rules() + contract

    user_message = f"""PROFILE (source of truth for accomplishments, skills, and details):
{profile_text}

PRIOR RESUME (source of truth for which bullets belong to which employer):
{resume_text}

JOB POSTING (tailor emphasis, ordering, and phrasing to this):
{job_text}"""
    if fact_bank:
        user_message += f"""

FACT BANK (authoritative, employer-tagged facts; build every bullet from these and cite their ids):
{format_fact_bank(fact_bank)}"""
    if deny_patterns:
        prohibited = "\n".join(f"- {p.pattern}" for p in deny_patterns)
        user_message += f"""

PROHIBITED CLAIMS (tier T4; case-insensitive regular expressions, and any match rejects the resume):
{prohibited}"""

    stage("drafting")
    print("  Drafting tailored content...")
    draft = invoke_claude(claude_bin, draft_system_prompt, user_message, model, effort)

    stage("structuring")
    print("  Converting to structured data...")
    parsed = None
    raw = ""
    for attempt in range(3):
        raw = invoke_claude(claude_bin, FORMAT_SYSTEM_PROMPT, draft, model, effort)
        parsed = _try_parse_format_json(raw, companies)
        total_bullets = sum(len(b) for b in (parsed or {}).get("bullets_by_company", {}).values())
        if parsed and parsed["summary"] and total_bullets:
            break
        print(f"  Attempt {attempt + 1} did not return usable structured data, retrying...")
    else:
        sys.exit(f"Could not get usable structured data after 3 attempts. Last raw response:\n{raw}")

    # The JSON-transcription step doesn't reliably flatten a categorized
    # skills section (e.g. "**Leadership:** Team Building | Change
    # Management") into the flat list we need — sometimes it drops whole
    # categories, sometimes it returns nothing at all. Parsing the draft's
    # skills section directly is far more reliable, so prefer it whenever it
    # finds anything.
    draft_skills = extract_skills_from_draft(draft)
    if draft_skills:
        parsed["skills"] = draft_skills

    parsed["draft"] = draft
    return parsed
