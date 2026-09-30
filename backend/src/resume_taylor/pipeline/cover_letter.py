"""Cover letter: one extra CLI call built only from the validated resume content and the
fact bank, then the same provenance rules as bullets."""

import re
import sys

from ..claude_cli import find_claude_cli, invoke_claude, strip_code_fence
from ..config import COVER_LETTER_SKILL_PATH
from .factbank import extract_citations, format_fact_bank
from .guards import remove_em_dashes, warn_unsupported_numbers
from .prompts import load_skill
from .runtime import warn


def draft_cover_letter(
    summary: str,
    bullets_by_company: dict,
    job_text: str,
    fact_bank: dict | None,
    deny_patterns: list,
    model: str | None = None,
    effort: str | None = None,
) -> list:
    """One extra CLI call, driven by the cover-letter skill, built only from the
    already-validated resume content (plus the fact bank). Returns the raw
    paragraphs, citations still attached."""
    bullets = "\n".join(
        f"{company}:\n" + "\n".join(f"- {b}" for b in bs) for company, bs in bullets_by_company.items()
    )
    user_message = f"""SUMMARY:
{summary}

BULLETS (final, validated resume content):
{bullets}

JOB POSTING:
{job_text}"""
    if fact_bank:
        user_message += f"\n\nFACT BANK (cite these ids):\n{format_fact_bank(fact_bank)}"
    if deny_patterns:
        prohibited = "\n".join(f"- {p.pattern}" for p in deny_patterns)
        user_message += f"\n\nPROHIBITED CLAIMS (case-insensitive regular expressions):\n{prohibited}"

    claude_bin = find_claude_cli()
    system_prompt = load_skill(COVER_LETTER_SKILL_PATH)
    raw = ""
    for attempt in range(3):
        raw = invoke_claude(claude_bin, system_prompt, user_message, model, effort)
        match = re.search(r"<COVER_LETTER>(.*?)</COVER_LETTER>", raw, re.DOTALL)
        body = strip_code_fence(match.group(1) if match else raw)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        if 2 <= len(paragraphs) <= 6:
            return paragraphs
        print(f"  Cover letter attempt {attempt + 1} was not usable, retrying...")
    sys.exit(f"Could not get a usable cover letter after 3 attempts. Last raw response:\n{raw}")


def validate_cover_letter(paragraphs: list, bank: dict | None, source_text: str) -> list:
    """Strip citations and apply the same provenance rules as bullets. Returns
    [(clean paragraph, ids)]. A paragraph citing an unknown or `unassigned`
    fact is dropped (hard evidence of fabrication); uncited paragraphs (other
    than the closing one) and numbers missing from the cited facts are warned
    about."""
    result = []
    for i, paragraph in enumerate(paragraphs, 1):
        text, ids = extract_citations(paragraph)
        text = remove_em_dashes(text)
        label = f"cover letter paragraph {i}"
        if bank:
            bad = [fid for fid in ids if fid not in bank or bank[fid]["employer"] == "unassigned"]
            if bad:
                warn(f"dropped {label}, which cites unknown/unassigned fact(s) {', '.join(bad)}: {text[:80]}...")
                continue
            if ids:
                cited = " ".join(
                    bank[f]["text"] + " " + " ".join(map(str, bank[f].get("metrics") or [])) for f in ids
                )
                warn_unsupported_numbers(text, f"{label} (vs. its cited facts)", cited)
            elif i < len(paragraphs):  # the closing paragraph carries no claims
                warn(f"uncited {label}, please verify: {text[:80]}...")
        warn_unsupported_numbers(text, label, source_text)
        result.append((text, ids))
    return result
