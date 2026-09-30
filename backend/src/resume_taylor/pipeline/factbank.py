"""The fact bank (hand-maintained, employer-tagged true facts) and the bullet citations
that tie every generated bullet back to it."""

import re
import sys
from pathlib import Path

import yaml

from ..config import FACT_BANK_PATH
from .guards import warn_unsupported_numbers
from .runtime import warn


def snap_employer(employer: str, companies: list) -> str | None:
    """Map an employer label onto a parsed company name case/whitespace-
    insensitively, or onto "general"/"unassigned". None if it matches nothing."""
    norm = lambda s: re.sub(r"\s+", " ", str(s).strip().lower())
    by_norm = {norm(c): c for c in companies}
    by_norm.update({"general": "general", "unassigned": "unassigned"})
    return by_norm.get(norm(employer))


def load_fact_bank(companies: list, path: Path | None = None) -> dict | None:
    """Load resume_input/fact_bank.yaml as {id: fact}. Returns None when absent,
    in which case the pipeline runs without citation enforcement.

    Employer labels are snapped to the parsed company names. A label matching
    no employer (usually a typo, or a renamed company) would silently make
    every such fact un-citable, so it is warned about and treated as
    `unassigned`."""
    path = path or FACT_BANK_PATH
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    bank = {}
    unknown = {}
    for fact in data.get("facts") or []:
        fid = str(fact.get("id", "")).strip().upper()
        if not fid or not fact.get("text"):
            continue
        if fid in bank:
            sys.exit(f"Duplicate fact id {fid} in {path.name}; ids must be unique.")
        raw_employer = str(fact.get("employer", "unassigned")).strip()
        employer = snap_employer(raw_employer, companies)
        if employer is None:
            unknown.setdefault(raw_employer, []).append(fid)
            employer = "unassigned"
        bank[fid] = {**fact, "id": fid, "employer": employer}
    for raw_employer, fids in unknown.items():
        warn(
            f"{path.name}: employer {raw_employer!r} matches no employer in the prior resume "
            f"({', '.join(companies)}); treating {', '.join(fids)} as unassigned (uncitable)."
        )
    unassigned = sum(1 for f in bank.values() if f["employer"] == "unassigned")
    if unassigned:
        warn(f"{path.name}: {unassigned} fact(s) are `unassigned` and can't back any bullet.")
    return bank or None


def format_fact_bank(bank: dict) -> str:
    return "\n".join(f"{fid} [{f['employer']}] {f['text']}" for fid, f in bank.items())


CITATION_RE = re.compile(r"\s*\[\s*(F\d+(?:\s*,\s*F\d+)*)\s*\]\s*\.?\s*$", re.IGNORECASE)


def split_citation(bullet: str) -> tuple:
    """Split 'Did X. [F001, F004]' into ('Did X.', ['F001', 'F004'])."""
    match = CITATION_RE.search(bullet)
    if not match:
        return bullet.strip(), []
    ids = [i.strip().upper() for i in match.group(1).split(",")]
    text = bullet[: match.start()].rstrip()
    if text and text[-1] not in ".!?":
        text += "."
    return text, ids


def validate_citations(bullets_by_company: dict, bank: dict) -> tuple:
    """Strip citation brackets from every bullet and enforce provenance.

    Dropped (hard evidence of fabrication or transplant): a bullet citing an
    unknown id, an `unassigned` fact, or another employer's fact.
    Warned (kept for manual review): a bullet with no citation at all, and a
    number in the bullet that doesn't appear in any fact it cites.

    Returns (clean bullets_by_company, citations_by_company) where the second
    maps each company to a list of id-lists parallel to its kept bullets."""
    cleaned, citations = {}, {}
    for company, bullets in bullets_by_company.items():
        kept, kept_ids = [], []
        for bullet in bullets:
            text, ids = split_citation(bullet)
            problem = None
            for fid in ids:
                fact = bank.get(fid)
                if fact is None:
                    problem = f"cites unknown fact {fid}"
                elif fact["employer"] == "unassigned":
                    problem = f"cites {fid}, which is `unassigned` in the fact bank"
                elif fact["employer"] not in (company, "general"):
                    problem = f"cites {fid}, a fact from {fact['employer']}"
                if problem:
                    break
            if problem:
                warn(f"dropped a bullet under {company} that {problem}: {text[:80]}...")
                continue
            if not ids:
                warn(f"uncited bullet under {company}, please verify: {text[:80]}...")
            else:
                cited_text = " ".join(
                    bank[fid]["text"] + " " + " ".join(map(str, bank[fid].get("metrics") or []))
                    for fid in ids
                )
                warn_unsupported_numbers(text, f"a bullet under {company} (vs. its cited facts)", cited_text)
            kept.append(text)
            kept_ids.append(ids)
        cleaned[company] = kept
        citations[company] = kept_ids
    return cleaned, citations


INLINE_CITATION_RE = re.compile(r"\s*\[\s*(F\d+(?:\s*,\s*F\d+)*)\s*\]", re.IGNORECASE)


def extract_citations(text: str) -> tuple:
    """Remove every '[F001, F004]' group anywhere in text (a paragraph may cite
    mid-sentence, unlike a bullet); return (clean text, ids in order)."""
    ids = []
    for group in INLINE_CITATION_RE.findall(text):
        for fid in group.split(","):
            fid = fid.strip().upper()
            if fid not in ids:
                ids.append(fid)
    clean = INLINE_CITATION_RE.sub("", text)
    clean = re.sub(r"\s+([.,;:!?])", r"\1", clean)
    return re.sub(r"\s{2,}", " ", clean).strip(), ids
