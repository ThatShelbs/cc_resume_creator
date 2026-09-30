"""The Markdown tailoring report (the audit trail read before a resume is sent)."""

from datetime import datetime
from pathlib import Path


def write_report(
    path: Path,
    inputs: dict,
    model: str,
    effort: str,
    warnings: list,
    coverage: tuple,
    bullets_by_company: dict,
    citations: dict | None,
    fact_bank: dict | None,
    draft: str,
    cover_letter: list | None = None,
    page_count: int | None = None,
) -> None:
    """Markdown audit trail for one run: what went in, every advisory warning,
    keyword coverage, each final bullet with the facts it cites, and the raw
    draft. Meant to be read before the resume is sent. `citations` maps
    (company, final bullet text) -> cited fact ids."""
    covered, missing = coverage
    lines = [
        f"# Tailoring report ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
        "",
        f"- Model: {model} (effort={effort})",
        *(f"- {label}: `{name}`" for label, name in inputs.items()),
        *([f"- Resume length: {page_count} page(s)"] if page_count else []),
        "",
        f"## Warnings ({len(warnings)})",
        "",
        *([f"- {w}" for w in warnings] or ["None."]),
        "",
        f"## Keyword coverage ({len(covered)}/{len(covered) + len(missing)})",
        "",
        "Posting terms the candidate genuinely has (from the profile's skills/tools "
        "and the fact bank's tags).",
        "",
        f"- Covered: {', '.join(covered) or 'none'}",
        f"- Missing: {', '.join(missing) or 'none'}",
        "",
        "## Bullets and provenance",
        "",
    ]
    for company, bullets in bullets_by_company.items():
        lines += [f"### {company}", ""]
        for bullet in bullets:
            ids = (citations or {}).get((company, bullet), [])
            lines.append(f"- {bullet}")
            for fid in ids:
                fact = (fact_bank or {}).get(fid)
                if fact:
                    lines.append(f"  - `{fid}` {fact['text']}")
            if fact_bank and not ids:
                lines.append("  - (uncited)")
        lines.append("")
    if cover_letter:
        lines += ["## Cover letter", ""]
        for text, ids in cover_letter:
            lines += [text, ""]
            for fid in ids:
                fact = (fact_bank or {}).get(fid)
                if fact:
                    lines.append(f"- `{fid}` {fact['text']}")
            lines.append("")
    lines += ["## Raw draft", "", "```", draft.strip(), "```", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
