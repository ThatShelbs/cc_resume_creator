"""The Claude-backed half of a run: draft, structure, validate, and assemble the result."""

import argparse
import sys
from datetime import datetime

from .cover_letter import draft_cover_letter, validate_cover_letter
from .coverage import keyword_coverage
from .factbank import split_citation, validate_citations
from .guards import (
    find_deny_violations,
    fix_years_of_experience,
    remove_em_dashes,
    strip_cross_employer_mentions,
    warn_analogy_phrasing,
    warn_unsupported_numbers,
    warn_unverified_skills,
)
from .result import RESULT_SCHEMA, report_deny_violations
from .runtime import stage, warn
from .skills import merge_and_sort_skills
from .tailoring import tailor_content


def generate(args: argparse.Namespace, ctx: dict) -> dict:
    """The Claude-backed half: draft, structure, and validate. Returns a result dict."""
    fact_bank = ctx["fact_bank"]
    parsed_resume = ctx["parsed_resume"]
    resume_text, job_text = ctx["resume_text"], ctx["job_text"]
    deny_patterns = ctx["deny_patterns"]

    print(f"Tailoring content with {args.model} (effort={args.effort})...")
    tailored = tailor_content(
        ctx["profile_text"],
        resume_text,
        job_text,
        parsed_resume["jobs"],
        deny_patterns,
        fact_bank,
        model=args.model,
        effort=args.effort,
    )

    stage("validating")
    summary = fix_years_of_experience(tailored["summary"], resume_text)
    summary = remove_em_dashes(summary)
    bullets_by_company = tailored["bullets_by_company"]
    citations = {}
    if fact_bank:
        bullets_by_company, cited = validate_citations(bullets_by_company, fact_bank)
        # Key by final (em-dash-cleaned) text: later steps only drop bullets,
        # so this stays correct where position-based lists would not.
        citations = {
            (c, remove_em_dashes(b)): ids
            for c, bs in bullets_by_company.items()
            for b, ids in zip(bs, cited[c])
        }
    else:
        bullets_by_company = {c: [split_citation(b)[0] for b in bs] for c, bs in bullets_by_company.items()}
    bullets_by_company = strip_cross_employer_mentions(bullets_by_company)
    bullets_by_company = {c: [remove_em_dashes(b) for b in bs] for c, bs in bullets_by_company.items()}
    warn_analogy_phrasing(bullets_by_company)

    profile_skills = ctx["profile_skills"]
    skills = merge_and_sort_skills(tailored["skills"], profile_skills, job_text)

    source_text = ctx["source_text"]
    warn_unsupported_numbers(summary, "the summary", source_text)
    for company, bullets in bullets_by_company.items():
        for bullet in bullets:
            warn_unsupported_numbers(bullet, f"a bullet under {company}", source_text)
    warn_unverified_skills(skills, source_text)

    violations = find_deny_violations(summary, bullets_by_company, skills, deny_patterns)
    if violations:
        report_deny_violations(violations, ctx["deny_name"])

    experience = []
    for job in parsed_resume["jobs"]:
        bullets = bullets_by_company.get(job["company"])
        if not bullets:
            warn(
                f"no tailored bullets survived for {job['company']}; using the prior "
                "resume's bullets for it unchanged."
            )
            bullets = job["source_bullets"]
            bullets_by_company[job["company"]] = bullets
        experience.append(
            {
                "company": job["company"],
                "location": job["location"],
                "dates": job["dates"],
                "title": job["title"],
                "bullets": [
                    {"text": b, "ids": citations.get((job["company"], b), [])} for b in bullets
                ],
            }
        )

    output_text = "\n".join([summary, *(b for bs in bullets_by_company.values() for b in bs), *skills])
    covered, missing = keyword_coverage(job_text, output_text, profile_skills, fact_bank)
    print(
        f"Keyword coverage: {len(covered)}/{len(covered) + len(missing)} posting terms you "
        "have appear in the resume."
    )
    if missing:
        print(f"  Not used: {', '.join(missing)}")

    cover_letter = None
    if args.cover_letter:
        stage("cover_letter")
        print("Drafting cover letter...")
        cover_letter = validate_cover_letter(
            draft_cover_letter(
                summary, bullets_by_company, job_text, fact_bank, deny_patterns, args.model, args.effort
            ),
            fact_bank,
            source_text,
        )
        if not cover_letter:
            sys.exit("Every cover letter paragraph failed validation. Nothing was archived; re-run.")
        cl_violations = find_deny_violations(
            "\n".join(text for text, _ in cover_letter), {}, [], deny_patterns
        )
        if cl_violations:
            report_deny_violations([("cover letter", p, t) for _, p, t in cl_violations], ctx["deny_name"])

    return {
        "schema": RESULT_SCHEMA,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": args.model,
        "effort": args.effort,
        "template": args.template,
        "inputs": ctx["inputs"],
        "contact": ctx["contact"],
        "summary": summary,
        "education": parsed_resume["education"],
        "experience": experience,
        "skills": skills,
        "cover_letter": [{"text": t, "ids": ids} for t, ids in cover_letter] if cover_letter else None,
        "coverage": {"covered": covered, "missing": missing},
        "page_count": None,
        "draft": tailored["draft"],
    }
