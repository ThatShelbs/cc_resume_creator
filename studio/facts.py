"""The fact bank (resume_input/fact_bank.yaml) and the never-claim list
(do_not_claim.txt) as editable data. Both files stay hand-readable: saving
keeps the fact bank's comment header and the deny list's comments."""

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator

import generate_resume as g

FACT_KINDS = ["accomplishment", "responsibility", "project", "skill", "tool", "trait", "award"]
FACT_ID_RE = re.compile(r"^F\d{3,}$")


class Fact(BaseModel):
    id: str = ""
    employer: str = "unassigned"
    kind: str = "accomplishment"
    text: str
    metrics: list[str] = []
    tags: list[str] = []

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        v = re.sub(r"\s+", " ", v).strip()
        if not v:
            raise ValueError("fact text can't be empty")
        return v


class FactBankError(ValueError):
    pass


def _header(path: Path) -> str:
    if not path.exists():
        return ""
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            lines.append(line)
        else:
            break
    return "\n".join(lines).rstrip() + "\n\n" if lines else ""


def read_facts(path: Path) -> list[Fact]:
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise FactBankError(f"{path.name} isn't valid YAML: {exc}") from None
    facts = []
    for raw in data.get("facts") or []:
        if not raw or not str(raw.get("text", "")).strip():
            continue
        facts.append(
            Fact(
                id=str(raw.get("id", "")).strip().upper(),
                employer=str(raw.get("employer", "unassigned")).strip() or "unassigned",
                kind=str(raw.get("kind", "accomplishment")).strip().lower(),
                text=str(raw["text"]),
                metrics=[str(m) for m in raw.get("metrics") or []],
                tags=[str(t) for t in raw.get("tags") or []],
            )
        )
    return facts


def assign_ids(facts: list[Fact]) -> list[Fact]:
    """Keep existing ids stable (resumes cite them); give new facts the next free id."""
    used = {f.id for f in facts if FACT_ID_RE.match(f.id)}
    next_n = max((int(i[1:]) for i in used), default=0) + 1
    seen = set()
    for fact in facts:
        if not FACT_ID_RE.match(fact.id) or fact.id in seen:
            while f"F{next_n:03d}" in used:
                next_n += 1
            fact.id = f"F{next_n:03d}"
            used.add(fact.id)
            next_n += 1
        seen.add(fact.id)
    return facts


def write_facts(path: Path, facts: list[Fact]) -> None:
    facts = assign_ids(facts)
    header = _header(path) or (
        "# Fact bank: the source of truth for tailoring. Every resume bullet must cite\n"
        "# the ids of the facts it is built from. Edited in Resume Studio or by hand.\n\n"
    )
    body = yaml.safe_dump(
        {"facts": [f.model_dump() for f in facts]}, sort_keys=False, allow_unicode=True, width=100
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(header + body, encoding="utf-8")
    tmp.replace(path)


def employer_issues(facts: list[Fact], companies: list[str]) -> list[dict]:
    """Facts whose employer label matches no employer in the base resume.
    The pipeline would treat them as `unassigned` (uncitable)."""
    issues = []
    for fact in facts:
        if g.snap_employer(fact.employer, companies) is None:
            issues.append({"id": fact.id, "employer": fact.employer})
    return issues


# ---------------------------------------------------------------------------
# Never-claim list
# ---------------------------------------------------------------------------


def read_deny_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def check_deny_text(text: str) -> list[dict]:
    """One entry per pattern line: {line, pattern, error}."""
    results = []
    for n, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            re.compile(stripped, re.IGNORECASE)
            results.append({"line": n, "pattern": stripped, "error": None})
        except re.error as exc:
            results.append({"line": n, "pattern": stripped, "error": str(exc)})
    return results


def write_deny_text(path: Path, text: str) -> None:
    bad = [r for r in check_deny_text(text) if r["error"]]
    if bad:
        first = bad[0]
        raise FactBankError(f"Line {first['line']} isn't a valid pattern: {first['error']}")
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def match_phrase(text: str, phrase: str) -> list[str]:
    """Which patterns a sample phrase would trip."""
    return [
        r["pattern"]
        for r in check_deny_text(text)
        if not r["error"] and re.search(r["pattern"], phrase, re.IGNORECASE)
    ]
