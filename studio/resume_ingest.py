"""
Turn an uploaded resume (Word or PDF) into the structure the pipeline needs,
then write it back out as a normalized in_resume*.docx that
parse_prior_resume() reads exactly.

Order of preference, most deterministic first:
  1. A .docx already in the pipeline layout parses directly.
  2. Otherwise the text is parsed heuristically (section headings, date-range
     entry headers, bullet markers, wrapped-line joining).
  3. Only if that finds no employers, one Claude CLI call extracts the
     structure verbatim. Run it as a job: `python -m studio.resume_ingest --ai`.

Whichever path ran, every company, title, date, and bullet is checked against
the raw text and anything not found verbatim is flagged for the review screen.
Nothing is written until a person confirms the structure.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import docx
from pydantic import BaseModel

from . import CODE_ROOT  # noqa: F401  (puts the pipeline on sys.path)
import generate_resume as g


class Education(BaseModel):
    institution: str = ""
    location: str = ""
    dates: str = ""
    degree: str = ""


class Job(BaseModel):
    company: str = ""
    location: str = ""
    dates: str = ""
    title: str = ""
    bullets: list[str] = []


class OtherSection(BaseModel):
    title: str
    lines: list[str] = []


class Flag(BaseModel):
    path: str  # e.g. "jobs.0.bullets.2"
    message: str


class ResumeStructure(BaseModel):
    summary: str = ""
    education: list[Education] = []
    jobs: list[Job] = []
    other_sections: list[OtherSection] = []
    flags: list[Flag] = []
    source: str = ""  # "docx" | "heuristic" | "ai" | "current"
    source_file: str = ""
    raw_text: str = ""
    contact_lines: list[str] = []


class IngestError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

BULLET_CHARS = "•●▪◦‣∙·■□➢➤►–-*"
BULLET_RE = re.compile(rf"^\s*[{re.escape(BULLET_CHARS)}]\s+|^\s*[•●▪◦]\s*")


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        try:
            pages = PdfReader(str(path)).pages
        except Exception as exc:  # pypdf raises many types on malformed files
            raise IngestError(f"Could not read that PDF ({exc}).") from None
        text = "\n".join((page.extract_text() or "") for page in pages).strip()
        if not text:
            raise IngestError("That PDF has no selectable text (it may be a scanned image). Upload the Word version instead.")
        return text
    if suffix == ".docx":
        d = g.open_docx(path)
        lines = []
        for p in d.paragraphs:
            if not p.text.strip():
                continue
            is_list = p.style.name.lower().startswith("list") or p._p.pPr is not None and p._p.pPr.numPr is not None
            lines.append(("• " if is_list and not BULLET_RE.match(p.text) else "") + p.text.rstrip())
        for table in d.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    lines.append("\t".join(dict.fromkeys(cells)))
        return "\n".join(lines)
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")
    raise IngestError("Upload a .pdf or .docx resume.")


# ---------------------------------------------------------------------------
# Heuristic parser
# ---------------------------------------------------------------------------

SECTION_ALIASES = {
    "summary": {"summary", "professional summary", "profile", "professional profile", "about", "about me",
                "career summary", "executive summary", "objective", "overview"},
    "experience": {"experience", "professional experience", "work experience", "employment",
                   "employment history", "work history", "career history", "relevant experience"},
    "education": {"education", "education & training", "education and training", "academic background"},
    "skills": {"skills", "core competencies", "technical skills", "skills & tools", "skills and tools",
               "competencies", "key skills", "areas of expertise", "tools", "technologies"},
}
OTHER_SECTIONS = {"projects", "awards", "certifications", "publications", "volunteer", "volunteering",
                  "honors", "honors & awards", "awards & recognition", "languages", "interests",
                  "leadership", "patents", "presentations", "speaking", "affiliations", "training"}

MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE_POINT = rf"(?:{MONTH}\s+)?(?:\d{{1,2}}/)?(?:19|20)\d{{2}}"
DATE_RANGE_RE = re.compile(
    rf"({DATE_POINT}\s*(?:-|–|—|to|through)\s*(?:{DATE_POINT}|present|current|now|today))",
    re.IGNORECASE,
)
SINGLE_DATE_RE = re.compile(rf"({DATE_POINT})\s*$", re.IGNORECASE)


def _heading_key(line: str) -> str | None:
    key = re.sub(r"[:#*_]+", "", line).strip().lower()
    key = re.sub(r"\s+", " ", key)
    if not key or len(key) > 40:
        return None
    for section, aliases in SECTION_ALIASES.items():
        if key in aliases:
            return section
    if key in OTHER_SECTIONS:
        return "other"
    return None


def _split_place(text: str) -> tuple:
    """'Company | City, ST' / 'Company, City, ST' / 'Company – City' -> (company, location)."""
    text = text.strip(" \t|,-–—")
    for sep in ("|", "\t", " – ", " — ", " - ", " · ", " • "):
        if sep in text:
            left, _, right = text.partition(sep)
            return left.strip(" \t|,"), right.strip(" \t|,")
    # "Company, City, ST" or "Company, City, State"
    match = re.match(r"^(.+?),\s*([^,]+,\s*(?:[A-Z]{2}|[A-Z][a-z]+(?: [A-Z][a-z]+)?))$", text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return text, ""


def _is_bullet(line: str) -> bool:
    return bool(BULLET_RE.match(line))


def _strip_bullet(line: str) -> str:
    return BULLET_RE.sub("", line, count=1).strip()


def _join_wrapped(prev: str, nxt: str) -> str:
    if prev.endswith("-") and nxt[:1].islower():
        return prev[:-1] + nxt
    return f"{prev} {nxt}"


def _parse_entries(lines: list, kind: str) -> list:
    """Entries of {head, dates, detail, bullets} from one section's lines."""
    entries = []
    current = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if _is_bullet(line):
            if current is None:
                current = {"head": "", "dates": "", "detail": "", "bullets": []}
                entries.append(current)
            current["bullets"].append(_strip_bullet(line))
            current["marked"] = True
            continue
        match = DATE_RANGE_RE.search(line) or (SINGLE_DATE_RE.search(line) if kind == "education" else None)
        if match:
            head = (line[: match.start()] + " " + line[match.end():]).strip(" \t|,-–—()")
            if not head and current is not None and not current["bullets"] and not current["dates"]:
                current["dates"] = match.group(1).strip()  # dates on their own line under the header
                continue
            current = {"head": head, "dates": match.group(1).strip(), "detail": "", "bullets": []}
            entries.append(current)
            continue
        if current is None:
            current = {"head": line, "dates": "", "detail": "", "bullets": []}
            entries.append(current)
        elif current["bullets"] and (
            current.get("marked")
            or line[:1].islower()
            or not current["bullets"][-1].rstrip().endswith((".", "!", "?"))
        ):
            # A wrapped continuation of the previous bullet (PDF line breaks).
            # With bullet glyphs every unmarked line is one; without them, a
            # line only continues a bullet that hasn't finished its sentence.
            current["bullets"][-1] = _join_wrapped(current["bullets"][-1], line)
        elif not current["detail"]:
            current["detail"] = line
        elif not current["head"]:
            current["head"] = line
        else:
            # Past the title line, unmarked lines are bullets whose glyphs
            # didn't survive text extraction.
            current["bullets"].append(line)
    return [e for e in entries if e["head"] or e["bullets"]]


def _looks_like_place(text: str) -> bool:
    return bool(_split_place(text)[1])


def _orient(head: str, detail: str) -> tuple:
    """Return (place line, title line). Some layouts lead with the title and
    put "Company | City" underneath; swap those back."""
    if not _looks_like_place(head) and _looks_like_place(detail):
        return detail, head
    return head, detail


def heuristic_parse(text: str) -> ResumeStructure:
    sections: dict = {}
    order: list = []
    other_titles: dict = {}
    current = "_header"
    sections[current] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        key = _heading_key(line) if line.strip() and not _is_bullet(line) else None
        if key:
            current = key if key != "other" else f"other:{line.strip().rstrip(':').strip()}"
            if key == "other":
                other_titles[current] = line.strip().rstrip(":").strip().title()
            sections.setdefault(current, [])
            order.append(current)
            continue
        sections[current].append(line)

    structure = ResumeStructure(source="heuristic", raw_text=text)
    structure.contact_lines = [l.strip() for l in sections.get("_header", []) if l.strip()]
    structure.summary = " ".join(
        _strip_bullet(l) if _is_bullet(l) else l.strip() for l in sections.get("summary", []) if l.strip()
    )

    for e in _parse_entries(sections.get("experience", []), "experience"):
        place, title = _orient(e["head"], e["detail"])
        company, location = _split_place(place)
        structure.jobs.append(
            Job(company=company, location=location, dates=e["dates"], title=title, bullets=e["bullets"])
        )
    for e in _parse_entries(sections.get("education", []), "education"):
        institution, location = _split_place(e["head"])
        degree = e["detail"] or " ".join(e["bullets"])
        structure.education.append(
            Education(institution=institution, location=location, dates=e["dates"], degree=degree)
        )
    if sections.get("skills"):
        structure.other_sections.append(
            OtherSection(title="Skills", lines=[_strip_bullet(l) for l in sections["skills"] if l.strip()])
        )
    for key in order:
        if key.startswith("other:") and sections.get(key):
            structure.other_sections.append(
                OtherSection(title=other_titles[key], lines=[_strip_bullet(l) for l in sections[key] if l.strip()])
            )
    return structure


# ---------------------------------------------------------------------------
# The pipeline layout (docx paragraphs) <-> structure
# ---------------------------------------------------------------------------

PIPELINE_SECTIONS = {"summary", "education", "experience", "skills", "projects", "awards"}


def structure_from_paras(paras: list) -> ResumeStructure:
    """Read a resume that's already in the pipeline layout (the canonical
    in_resume*.docx), keeping the summary and other sections too."""
    parsed = g.parse_prior_resume(paras)
    structure = ResumeStructure(source="docx")
    current = None
    other: dict = {}
    prev_was_header = False
    for i, (style, text) in enumerate(paras):
        key = text.strip().rstrip(":").strip().lower()
        title = text.strip().rstrip(":").strip()
        next_style = paras[i + 1][0] if i + 1 < len(paras) else None
        if (
            style == "Normal"
            and isinstance(current, tuple)
            and next_style == "List Paragraph"
            and len(title) <= 40
            and key not in PIPELINE_SECTIONS
        ):
            # A heading we wrote for an extra section (its lines are always
            # List Paragraph), not a Normal-style content line like "Python, SQL".
            other[title] = []
            current = ("other", title)
            continue
        if style == "Normal" and key in PIPELINE_SECTIONS:
            current = key
            if key not in ("summary", "education", "experience"):
                other[title] = []
                current = ("other", title)
            prev_was_header = False
            continue
        if style == "Normal" and current in ("education", "experience") and "|" not in text and not prev_was_header:
            # A heading the pipeline doesn't know (e.g. "Certifications"): the
            # parser ignores its content, but the editor keeps it.
            other[title] = []
            current = ("other", title)
            continue
        prev_was_header = style == "Normal" and "|" in text
        if current == "summary":
            structure.summary = f"{structure.summary} {text.strip()}".strip()
        elif isinstance(current, tuple):
            other[current[1]].append(text.strip())
    structure.education = [Education(**e) for e in parsed["education"]]
    structure.jobs = [
        Job(company=j["company"], location=j["location"], dates=j["dates"], title=j["title"], bullets=j["source_bullets"])
        for j in parsed["jobs"]
    ]
    structure.other_sections = [OtherSection(title=t, lines=l) for t, l in other.items() if l]
    return structure


def _field(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("|", "/")).strip()


def structure_to_paras(structure: ResumeStructure) -> list:
    paras = []
    if structure.summary.strip():
        paras += [("Normal", "Summary"), ("Normal", _field(structure.summary))]
    if structure.education:
        paras.append(("Normal", "Education"))
        for e in structure.education:
            paras.append(("Normal", f"{_field(e.institution)} | {_field(e.location)}\t{_field(e.dates)}"))
            paras.append(("Normal", _field(e.degree) or " "))
    paras.append(("Normal", "Experience"))
    for j in structure.jobs:
        paras.append(("Normal", f"{_field(j.company)} | {_field(j.location)}\t{_field(j.dates)}"))
        paras.append(("Normal", _field(j.title) or " "))
        paras += [("List Paragraph", _field(b)) for b in j.bullets if _field(b)]
    for section in structure.other_sections:
        lines = [_field(l) for l in section.lines if _field(l)]
        if not lines:
            continue
        title = _field(section.title) or "Additional"
        # Other headings are always followed by List Paragraph lines, so a
        # "|" can never turn one of them into a phantom employer.
        paras.append(("Normal", title))
        paras += [("List Paragraph", l) for l in lines]
    return paras


def validate_structure(structure: ResumeStructure) -> None:
    if not structure.jobs:
        raise IngestError("Add at least one employer before saving.")
    for i, j in enumerate(structure.jobs, 1):
        if not _field(j.company):
            raise IngestError(f"Employer #{i} needs a company name.")
        if not _field(j.title):
            raise IngestError(f"Employer #{i} ({j.company}) needs a job title.")
    names = [_field(j.company).lower() for j in structure.jobs]
    if len(set(names)) != len(names):
        raise IngestError(
            "Two employers share the same company name. Add a distinguishing detail (e.g. a division) "
            "so bullets can't be attributed to the wrong one."
        )
    try:
        parsed = g.parse_prior_resume(structure_to_paras(structure))
    except SystemExit as exc:
        raise IngestError(str(exc)) from None
    if len(parsed["jobs"]) != len(structure.jobs):
        raise IngestError("The resume structure did not round-trip; check for unusual characters in employer lines.")


def write_resume_docx(structure: ResumeStructure, path: Path) -> None:
    validate_structure(structure)
    d = docx.Document()
    for style, text in structure_to_paras(structure):
        d.add_paragraph(text, style=style)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.docx")
    d.save(str(tmp))
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Verification against the source text
# ---------------------------------------------------------------------------


def _norm(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(rf"[{re.escape(BULLET_CHARS)}]", " ", text)
    text = re.sub(r"-\s*\n\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _words(text: str) -> list:
    return re.findall(r"[a-z0-9$%+.']+", _norm(text))


def _found(needle: str, haystack_norm: str, haystack_words: set) -> bool:
    n = _norm(needle)
    if not n or n in haystack_norm:
        return True
    words = _words(needle)
    if not words:
        return True
    hits = sum(1 for w in words if w in haystack_words)
    return hits / len(words) >= 0.9


def verify(structure: ResumeStructure, raw_text: str) -> ResumeStructure:
    """Flag any field that doesn't appear in the uploaded file's text."""
    hay = _norm(raw_text)
    hay_words = set(_words(raw_text))
    flags = []
    for i, j in enumerate(structure.jobs):
        for field in ("company", "title", "dates", "location"):
            value = getattr(j, field)
            if value and not _found(value, hay, hay_words):
                flags.append(Flag(path=f"jobs.{i}.{field}", message=f"'{value}' was not found in the uploaded file."))
        for k, b in enumerate(j.bullets):
            if not _found(b, hay, hay_words):
                flags.append(Flag(path=f"jobs.{i}.bullets.{k}", message="This bullet doesn't match the uploaded file verbatim."))
        if not j.title:
            flags.append(Flag(path=f"jobs.{i}.title", message="No job title was detected. Please add it."))
        if not j.dates:
            flags.append(Flag(path=f"jobs.{i}.dates", message="No dates were detected. Please add them."))
    for i, e in enumerate(structure.education):
        for field in ("institution", "degree", "dates"):
            value = getattr(e, field)
            if value and not _found(value, hay, hay_words):
                flags.append(Flag(path=f"education.{i}.{field}", message=f"'{value}' was not found in the uploaded file."))
    structure.flags = flags
    return structure


# ---------------------------------------------------------------------------
# Claude fallback (run as a subprocess job)
# ---------------------------------------------------------------------------

AI_SYSTEM_PROMPT = """You are a verbatim resume-structure extraction tool. You never \
rewrite, summarize, improve, merge, or invent anything. Copy every value character for \
character from the resume text you are given.

Return exactly this JSON shape, wrapped in <RESUME_STRUCTURE> and </RESUME_STRUCTURE> \
tags, with nothing else in your reply:
<RESUME_STRUCTURE>
{"summary": "summary paragraph or empty string",
 "education": [{"institution": "", "location": "", "dates": "", "degree": ""}],
 "jobs": [{"company": "", "location": "", "dates": "", "title": "", "bullets": ["..."]}],
 "other_sections": [{"title": "Skills", "lines": ["..."]}],
 "contact_lines": ["name", "email", "phone", "..."]}
</RESUME_STRUCTURE>

Rules: one "jobs" entry per employer and role, most recent first, in the order they \
appear. If a person held several titles at one employer, make one entry per title with \
the same company. Leave a field as "" when it is not in the text; never guess."""


def ai_parse(text: str) -> ResumeStructure:
    claude_bin = g._find_claude_cli()
    raw = ""
    for attempt in range(2):
        raw = g._invoke_claude(claude_bin, AI_SYSTEM_PROMPT, text)
        match = re.search(r"<RESUME_STRUCTURE>(.*?)</RESUME_STRUCTURE>", raw, re.DOTALL)
        try:
            data = json.loads(g._strip_code_fence(match.group(1) if match else raw))
            structure = ResumeStructure(**data)
            structure.source = "ai"
            return structure
        except (json.JSONDecodeError, ValueError, TypeError):
            print(f"  Attempt {attempt + 1} did not return a usable structure, retrying...")
    raise IngestError("Claude could not structure this resume. Try the Word version, or fill in the form by hand.")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def ingest(path: Path) -> ResumeStructure:
    """Deterministic ingestion only. The caller checks `.jobs` and offers the
    Claude fallback when it's empty."""
    if path.suffix.lower() == ".docx":
        try:
            structure = structure_from_paras(g.docx_paras(path, strip=False))
            if structure.jobs:
                structure.raw_text = g.read_docx_text(path)
                structure.source_file = path.name
                return verify(structure, structure.raw_text)
        except SystemExit:
            pass
    text = extract_text(path)
    structure = heuristic_parse(text)
    structure.source_file = path.name
    return verify(structure, text)


def prefill_contact(structure: ResumeStructure) -> dict:
    """Best-effort contact details from the resume header, for onboarding."""
    lines = structure.contact_lines
    pieces = []
    for line in lines:
        pieces += [p.strip() for p in re.split(r"\s*[|•·]\s*|\t", line) if p.strip()]
    email = next((m.group(0) for p in pieces if (m := re.search(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", p))), "")
    phone = next((m.group(0) for p in pieces if (m := g.PHONE_RE.search(p))), "")
    linkedin = next((p for p in pieces if "linkedin.com" in p.lower()), "")
    name = next(
        (p for p in pieces if p not in (email, linkedin) and not g.PHONE_RE.search(p) and "@" not in p
         and 1 < len(p.split()) <= 4 and not any(ch.isdigit() for ch in p)),
        "",
    )
    if name.isupper():
        name = name.title()  # small-caps headers extract as ALL CAPS
    location = next(
        (p for p in pieces if p not in (name, email, linkedin) and not g.PHONE_RE.search(p)
         and re.search(r",\s*[A-Z]{2}\b|,\s*[A-Z][a-z]+", p)),
        "",
    )
    skills = []
    for section in structure.other_sections:
        if section.title.lower() in SECTION_ALIASES["skills"]:
            for line in section.lines:
                label, _, rest = line.partition(":")
                items = rest if rest.strip() and len(label) < 30 else line
                skills += [s.strip() for s in re.split(r"[,|•·;]", items) if 1 < len(s.strip()) <= 60]
    return {"name": name, "email": email, "phone": phone, "location": location, "linkedin": linkedin,
            "skills": list(dict.fromkeys(skills))}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Structure an uploaded resume with one Claude call.")
    parser.add_argument("--ai", type=Path, required=True, help="uploaded .pdf/.docx")
    parser.add_argument("--out", type=Path, required=True, help="where to write the structure JSON")
    args = parser.parse_args(argv)
    g.stage("preparing")
    print(f"Reading {args.ai.name}...")
    try:
        text = extract_text(args.ai)
        g.stage("drafting")
        print("Asking Claude to structure the resume (verbatim extraction only)...")
        structure = ai_parse(text)
    except IngestError as exc:
        sys.exit(str(exc))
    g.stage("validating")
    structure.raw_text = text
    structure.source_file = args.ai.name
    verify(structure, text)
    print(f"Found {len(structure.jobs)} employer entries; {len(structure.flags)} field(s) flagged for review.")
    args.out.write_text(structure.model_dump_json(indent=2), encoding="utf-8")
    g.stage("done")


if __name__ == "__main__":
    main()
