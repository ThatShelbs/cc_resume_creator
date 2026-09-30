"""Deterministic validation/correction guards: cheap, precise checks that don't depend
on LLM self-compliance (inflated years, cross-employer bullets, unsupported numbers,
overclaiming phrasing, the never-claim list, em dashes)."""

import re
import sys
from pathlib import Path

from ..config import DO_NOT_CLAIM_EXAMPLE, DO_NOT_CLAIM_PATH
from .runtime import warn

YEARS_RE = re.compile(r"(\d+)\+?\s*years?\s+of\s+experience", re.IGNORECASE)


# The summary phrases tenure more loosely than the source ("15+ years leading",
# "over 12 years"), so match any "N years" there, not only "N years of experience".
SUMMARY_YEARS_RE = re.compile(r"(\d+)\+?\s*years?\b", re.IGNORECASE)


def fix_years_of_experience(summary: str, resume_text: str) -> str:
    source_match = YEARS_RE.search(resume_text)
    if not source_match:
        return summary
    source_years = int(source_match.group(1))

    def correct(match: re.Match) -> str:
        generated_years = int(match.group(1))
        if generated_years <= source_years + 2:
            return match.group(0)
        print(
            f"  Correcting inflated experience claim: '{match.group(0)}' -> "
            f"'{source_years}...' (source resume states {source_years} years)"
        )
        return str(source_years) + match.group(0)[len(match.group(1)):]

    return SUMMARY_YEARS_RE.sub(correct, summary)


# Generic first words that shouldn't be treated as a company's identifying
# keyword (would cause false-positive matches against unrelated bullets).
_GENERIC_COMPANY_WORDS = {"the", "american", "national", "united", "global", "first"}


def company_keywords(name: str) -> list:
    """Distinctive name(s) to search for — the full name, and its first word
    if that word is specific enough to be a reliable signal on its own (e.g.
    "Allstate" from "Allstate Insurance Company")."""
    keywords = [name]
    first_word = name.split()[0] if name.split() else ""
    if len(first_word) >= 4 and first_word.lower() not in _GENERIC_COMPANY_WORDS:
        keywords.append(first_word)
    return keywords


def strip_cross_employer_mentions(bullets_by_company: dict) -> dict:
    companies = list(bullets_by_company.keys())
    other_keywords = {
        company: [
            (other, kw) for other in companies if other != company for kw in company_keywords(other)
        ]
        for company in companies
    }
    cleaned = {}
    for company, bullets in bullets_by_company.items():
        kept = []
        for bullet in bullets:
            hit = next(
                (other for other, kw in other_keywords[company] if kw.lower() in bullet.lower()),
                None,
            )
            if hit:
                warn(
                    f"dropped a bullet under {company} that mentioned "
                    f"{hit} (cross-employer content is not allowed): {bullet[:80]}..."
                )
                continue
            kept.append(bullet)
        cleaned[company] = kept
    return cleaned


NUMBER_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s*[%KMB]?\+?")


def warn_unsupported_numbers(text: str, label: str, source_text: str) -> None:
    source_digits = {re.sub(r"[^\d]", "", n) for n in NUMBER_RE.findall(source_text)}
    for match in NUMBER_RE.findall(text):
        digits = re.sub(r"[^\d]", "", match)
        if len(digits) < 2:
            continue  # skip single-digit numbers (e.g. "3 direct reports") — too noisy to check
        if digits not in source_digits:
            warn(f"'{match}' in {label} was not found in the source documents, please verify.")


def warn_unverified_skills(skills: list, source_text: str) -> None:
    source_lower = source_text.lower()
    for skill in skills:
        core = re.sub(r"\s*\([^)]*\)", "", skill).strip().lower()
        if core and core not in source_lower:
            warn(f"skill '{skill}' wasn't found verbatim in the source documents, please verify.")


ANALOGY_RE = re.compile(
    r"\b(analogous to|directly applicable to|the same \w+ (?:used|applied) for)\b",
    re.IGNORECASE,
)


def warn_analogy_phrasing(bullets_by_company: dict) -> None:
    for company, bullets in bullets_by_company.items():
        for bullet in bullets:
            if ANALOGY_RE.search(bullet):
                warn(
                    f"a bullet under {company} uses comparison phrasing that "
                    f"may overclaim relevance to unfamiliar terms, please review: {bullet[:100]}..."
                )


def load_deny_patterns(path: Path | None = None) -> list:
    """Compile the hard "never claim" list. Missing file means no deny list."""
    path = path or DO_NOT_CLAIM_PATH
    if not path.exists() and path == DO_NOT_CLAIM_PATH:
        path = DO_NOT_CLAIM_EXAMPLE  # fresh download: fall back to the starter list
    if not path.exists():
        return []
    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            patterns.append(re.compile(line, re.IGNORECASE))
        except re.error as exc:
            sys.exit(f"Invalid regex in {path.name}: {line!r} ({exc})")
    return patterns


def find_deny_violations(summary: str, bullets_by_company: dict, skills: list, patterns: list) -> list:
    """Return (location, pattern, text) for every prohibited-claim match. Unlike
    the warn_* checks, a hit here is a hard failure: these are T4 claims
    (credentials, role identities, unsupported tools) that must never ship."""
    sections = [("summary", summary)]
    sections += [(f"bullet under {c}", b) for c, bs in bullets_by_company.items() for b in bs]
    sections += [("skills", s) for s in skills]
    return [
        (where, p.pattern, text)
        for where, text in sections
        for p in patterns
        if p.search(text)
    ]


def remove_em_dashes(text: str) -> str:
    """Backstop for the "no em dashes" style rule — prompt compliance isn't
    guaranteed, so replace any that slip through with a comma (safe for the
    fragment-style clauses resume bullets/summaries use)."""
    text = re.sub(r"\s*—\s*", ", ", text)
    # A spaced en dash (" – ") is the same tell; an unspaced one ("2019–2021")
    # is a range and stays.
    text = re.sub(r"\s+–\s+", ", ", text)
    return re.sub(r",\s*,", ",", text)
