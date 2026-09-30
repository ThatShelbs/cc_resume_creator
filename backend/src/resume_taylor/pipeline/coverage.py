"""Keyword coverage: which posting terms from the candidate's own vocabulary made it
into the resume."""

import re

from .skills import skill_key


def _contains_term(term: str, text_lower: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text_lower) is not None


def keyword_coverage(
    job_text: str, output_text: str, profile_skills: dict, fact_bank: dict | None
) -> tuple:
    """Which posting terms the candidate genuinely has actually made it into the
    resume. The vocabulary is only the candidate's own terms (profile
    tools/skills plus fact-bank tags), so every "missing" term is a truthful
    gap to consider, never an invitation to claim something new.

    Returns (covered, missing): terms named in the posting that do / don't
    appear in the output text."""
    vocab = {}
    candidates = profile_skills["tools"] + profile_skills["skills"]
    for fact in (fact_bank or {}).values():
        candidates += [str(t) for t in fact.get("tags") or []]
    for term in candidates:
        key = skill_key(term)
        if len(key) >= 2 and key not in vocab:
            vocab[key] = term.strip()

    job_lower, out_lower = job_text.lower(), output_text.lower()
    covered, missing = [], []
    for key, term in sorted(vocab.items()):
        if not _contains_term(key, job_lower):
            continue
        (covered if _contains_term(key, out_lower) else missing).append(term)
    return covered, missing
