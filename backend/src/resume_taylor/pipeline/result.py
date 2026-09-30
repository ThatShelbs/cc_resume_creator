"""The structured, editable result (--result-json) and its re-validation (--render-json):
re-run the guards over a result that may have been edited by hand, with no Claude call."""

import json
import os
import sys
from pathlib import Path

from .coverage import keyword_coverage
from .guards import (
    find_deny_violations,
    remove_em_dashes,
    warn_analogy_phrasing,
    warn_unsupported_numbers,
    warn_unverified_skills,
)
from .runtime import PROGRESS_MARKERS, WARNINGS, warn

RESULT_SCHEMA = 1


def result_citations(result: dict) -> dict:
    """(company, bullet text) -> cited fact ids, the shape write_report takes."""
    return {
        (job["company"], b["text"]): list(b.get("ids") or [])
        for job in result["experience"]
        for b in job["bullets"]
    }


def result_bullets_by_company(result: dict) -> dict:
    return {job["company"]: [b["text"] for b in job["bullets"]] for job in result["experience"]}


def result_to_docx_data(result: dict) -> dict:
    return {
        **result["contact"],
        "summary": result["summary"],
        "education": result.get("education") or [],
        "experience": [
            {**{k: job.get(k, "") for k in ("company", "location", "dates", "title")},
             "bullets": [b["text"] for b in job["bullets"]]}
            for job in result["experience"]
        ],
        "skills": result.get("skills") or [],
    }


def load_result(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"Could not read result JSON {path}: {exc}")
    for key in ("contact", "summary", "experience"):
        if key not in result:
            sys.exit(f"{path.name} is not a resume result file (missing '{key}').")
    return result


def save_result(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def report_deny_violations(violations: list, source_name: str) -> None:
    """Print every prohibited-claim hit and exit without writing anything."""
    for where, pattern, text in violations:
        print(f"  PROHIBITED CLAIM in {where} (matched {pattern!r}): {text[:120]}")
        if PROGRESS_MARKERS:
            print("::deny " + json.dumps({"where": where, "pattern": pattern, "text": text}), flush=True)
    sys.exit(
        f"Refusing to write the resume: {len(violations)} prohibited claim(s) from "
        f"{source_name}. Nothing was archived or overwritten."
    )


def revalidate_result(result: dict, ctx: dict) -> None:
    """Re-run the deterministic guards over a result that may have been edited
    by hand, in place. The model isn't involved, so nothing is dropped: an
    edit is a deliberate human choice, and every check becomes a warning to
    review. The one exception is the never-claim list, which stays a hard stop."""
    WARNINGS.clear()
    result["summary"] = remove_em_dashes(result["summary"].strip())
    for job in result["experience"]:
        job["bullets"] = [
            {"text": remove_em_dashes(b["text"].strip()), "ids": list(b.get("ids") or [])}
            for b in job["bullets"]
            if b.get("text", "").strip()
        ]
    result["skills"] = [s.strip() for s in result.get("skills") or [] if s.strip()]
    if result.get("cover_letter"):
        result["cover_letter"] = [
            {"text": remove_em_dashes(p["text"].strip()), "ids": list(p.get("ids") or [])}
            for p in result["cover_letter"]
            if p.get("text", "").strip()
        ]

    bullets_by_company = result_bullets_by_company(result)
    source_text = ctx["source_text"]
    bank = ctx["fact_bank"]

    if source_text:
        warn_unsupported_numbers(result["summary"], "the summary", source_text)
    for job in result["experience"]:
        company = job["company"]
        for b in job["bullets"]:
            text, ids = b["text"], b["ids"]
            if bank:
                if not ids:
                    warn(f"uncited bullet under {company}, please verify: {text[:80]}...")
                for fid in ids:
                    fact = bank.get(fid)
                    if fact is None:
                        warn(f"a bullet under {company} cites unknown fact {fid}: {text[:80]}...")
                    elif fact["employer"] not in (company, "general"):
                        warn(f"a bullet under {company} cites {fid}, a fact from {fact['employer']}: {text[:80]}...")
            if source_text:
                warn_unsupported_numbers(text, f"a bullet under {company}", source_text)
    warn_analogy_phrasing(bullets_by_company)
    if source_text:
        warn_unverified_skills(result["skills"], source_text)
        for i, p in enumerate(result.get("cover_letter") or [], 1):
            warn_unsupported_numbers(p["text"], f"cover letter paragraph {i}", source_text)

    violations = find_deny_violations(
        result["summary"], bullets_by_company, result["skills"], ctx["deny_patterns"]
    )
    violations += [
        ("cover letter", pattern, text)
        for _, pattern, text in find_deny_violations(
            "\n".join(p["text"] for p in result.get("cover_letter") or []), {}, [], ctx["deny_patterns"]
        )
    ]
    if violations:
        report_deny_violations(violations, ctx["deny_name"])

    if ctx["job_text"]:
        output_text = "\n".join(
            [result["summary"], *(b for bs in bullets_by_company.values() for b in bs), *result["skills"]]
        )
        covered, missing = keyword_coverage(ctx["job_text"], output_text, ctx["profile_skills"], bank)
        result["coverage"] = {"covered": covered, "missing": missing}
