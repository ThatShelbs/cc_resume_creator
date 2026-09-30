"""
Generate a tailored resume from the files in resume_input/.

Contact info, education, and each employer's company/location/dates/title are
extracted deterministically from resume_input/in_profile* and in_resume* —
there's no tailoring judgment involved in those fields, so the Claude Code CLI
(using your logged-in subscription, not a billed API key) is only asked to
produce the parts that actually require judgment: a tailored summary,
per-employer bullets selected from true source material, and a tailored skills
list (one drafting call, then a narrow JSON-transcription call). The result is
written to resume_create/ as .docx + .pdf + a _report.md audit trail; any
resume already there is moved to resume_archive/ (.docx and report only) first.

Requires the Claude Code CLI to be installed and logged in (`claude /login`).

Usage:
    python generate_resume.py [--job PATH] [--model M] [--effort E] [--no-pdf] [--dry-run]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import docx
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
import yaml
from dotenv import load_dotenv

INK = RGBColor(0x1F, 0x2A, 0x44)
MUTED = RGBColor(0x44, 0x44, 0x44)
RULE_COLOR = "1F2A44"

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "resume_input"
CREATE_DIR = ROOT / "resume_create"
ARCHIVE_DIR = ROOT / "resume_archive"

# Load .env before reading any setting from the environment (build_fact_bank.py
# imports this module, so it picks these up too).
load_dotenv(ROOT / ".env")

MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")
EFFORT = os.environ.get("CLAUDE_EFFORT", "medium")
CLAUDE_TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT", "600"))  # seconds per CLI call

# Every advisory warning raised during a run, collected for the report.
WARNINGS: list = []


def warn(msg: str) -> None:
    print(f"  Warning: {msg}")
    WARNINGS.append(msg)


# Resume Taylor (the browser app) runs this script as a subprocess and sets
# TAYLOR_PROGRESS=1 so it can follow along. The "::stage <name>" lines it then
# gets are a stable, machine-readable progress signal, so the app never has to
# parse the human-facing messages. Plain CLI runs don't print them.
PROGRESS_MARKERS = os.environ.get("TAYLOR_PROGRESS") == "1"


def stage(name: str) -> None:
    if PROGRESS_MARKERS:
        print(f"::stage {name}", flush=True)

# The tailoring rules/methodology live in an agent-native Claude Code skill
# (.claude/skills/resume-tailoring/SKILL.md) rather than in a Python string, so
# there's one source of truth shared by this pipeline and any interactive
# `/resume-tailoring` use. load_tailoring_rules() reads that file's body.
TAILORING_SKILL_PATH = ROOT / ".claude" / "skills" / "resume-tailoring" / "SKILL.md"
COVER_LETTER_SKILL_PATH = ROOT / ".claude" / "skills" / "cover-letter" / "SKILL.md"

# Hard "never claim" list (claim tier T4 in the skill): one regex per line.
DO_NOT_CLAIM_PATH = ROOT / "do_not_claim.txt"
DO_NOT_CLAIM_EXAMPLE = ROOT / "do_not_claim.example.txt"  # tracked starter list

# Hand-maintained bank of atomic, employer-tagged facts (drafted by
# build_fact_bank.py). When present, every bullet must cite fact ids from it.
FACT_BANK_PATH = INPUT_DIR / "fact_bank.yaml"


def open_docx(path: Path) -> docx.Document:
    # python-docx reports a file Word has open and locked as "Package not
    # found", which hides the real (and easily fixed) cause.
    try:
        with open(path, "rb"):
            pass
    except PermissionError:
        sys.exit(f"{path.name} is locked, most likely open in Word. Close it and re-run.")
    return docx.Document(str(path))


def read_docx_text(path: Path) -> str:
    d = open_docx(path)
    lines = [p.text for p in d.paragraphs if p.text.strip()]
    for table in d.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)


JOB_POSTING_EXTS = (".docx", ".pdf", ".txt", ".md")


def read_input_text(path: Path) -> str:
    """Plain text of an input whose structure isn't parsed (the job posting),
    so it can be saved however is convenient: .docx, .pdf, .txt, or .md."""
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return read_docx_text(path)
    if suffix == ".pdf":
        from pypdf import PdfReader

        return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages).strip()
    return path.read_text(encoding="utf-8", errors="replace").strip()


def count_pdf_pages(path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(path)).pages)


def find_latest(prefix: str, exts: tuple = (".docx",)) -> Path:
    """Newest matching file by modification time (not name, which would pick
    an alphabetically-last posting over the one just dropped in)."""
    candidates = [p for p in INPUT_DIR.glob(f"{prefix}*") if p.suffix.lower() in exts]
    matches = sorted(candidates, key=lambda p: p.stat().st_mtime)
    if not matches:
        sys.exit(
            f"No {'/'.join(exts)} file starting with '{prefix}' found in {INPUT_DIR}. "
            f"Expected a profile and prior resume (in_profile*.docx, in_resume*.docx) and a "
            f"job posting (in_job*: {', '.join(JOB_POSTING_EXTS)})."
        )
    return matches[-1]


# ---------------------------------------------------------------------------
# Deterministic extraction — no LLM involved, and none needed: contact info,
# education, and each job's company/location/dates/title carry no tailoring
# judgment, so parsing them straight out of the source .docx files is both
# faster and more accurate than asking a model to reproduce them.
# ---------------------------------------------------------------------------

PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")


def docx_paras(path: Path, strip: bool = True) -> list:
    """The (style name, text) pairs of every non-empty paragraph. The parsers
    below work on this list, so a caller that already has the structure (the
    Resume Taylor profile editor, a normalized uploaded resume) can hand it
    over directly instead of round-tripping through a file."""
    doc = open_docx(path)
    return [
        (p.style.name, p.text.strip() if strip else p.text) for p in doc.paragraphs if p.text.strip()
    ]


def _paras_and_name(source, strip: bool = True) -> tuple:
    if isinstance(source, (str, Path)):
        return docx_paras(Path(source), strip), Path(source).name
    return [(style, text.strip() if strip else text) for style, text in source], "the profile"


def parse_applicant_info(profile) -> dict:
    """`profile` is a .docx path or a list of (style, text) paragraphs."""
    paras, profile_name = _paras_and_name(profile)

    headings = ("applicant info", "contact", "contact info")
    lines = []
    in_section = False
    for style, text in paras:
        if not in_section:
            if text.lower().rstrip(":") in headings:
                in_section = True
            continue
        if style == "Normal" and text.lower().rstrip(":") not in headings:
            break
        lines.append(text)

    email = next((line for line in lines if "@" in line), "")
    phone = next((line for line in lines if PHONE_RE.search(line)), "")
    linkedin = next((line for line in lines if "linkedin.com" in line.lower()), "")
    remaining = [line for line in lines if line not in (email, phone, linkedin)]

    first_name, last_name, location = "", "", ""
    if remaining:
        parts = remaining[0].split()
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
    if len(remaining) > 1:
        location = ", ".join(remaining[1:])

    if not first_name or not email:
        sys.exit(
            f"Could not find name/email under an 'Applicant info' section in {profile_name}. "
            "Expected a section with the applicant's name, email, phone, and location as separate lines."
        )

    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "location": location,
        "linkedin": linkedin,
    }


def _split_header_line(text: str) -> tuple:
    """Split a 'Name | Location <tabs> Dates' line into (name, location, dates)."""
    name, _, rest = text.partition("|")
    location, _, dates = rest.partition("\t")
    return name.strip(), location.strip(), dates.strip(" \t")


def _parse_dated_entries(paras: list) -> list:
    """Parse (style, text) pairs into entries of {name, location, dates, detail, bullets}."""
    entries = []
    i = 0
    while i < len(paras):
        style, text = paras[i]
        if style != "Normal" or "|" not in text:
            i += 1
            continue
        name, location, dates = _split_header_line(text)
        i += 1
        detail = ""
        if i < len(paras) and paras[i][0] == "Normal":
            detail = paras[i][1].strip()
            i += 1
        bullets = []
        while i < len(paras) and paras[i][0] == "List Paragraph":
            bullets.append(paras[i][1].strip())
            i += 1
        entries.append(
            {"name": name, "location": location, "dates": dates, "detail": detail, "bullets": bullets}
        )
    return entries


def parse_prior_resume(resume) -> dict:
    """`resume` is a .docx path or a list of (style, text) paragraphs."""
    paras, resume_name = _paras_and_name(resume, strip=False)

    section_names = {"summary", "education", "experience", "skills", "projects", "awards"}
    sections = {}
    current = None
    for style, text in paras:
        key = text.strip().rstrip(":").strip().lower()
        if style == "Normal" and key in section_names:
            current = key
            sections[current] = []
            continue
        if current:
            sections[current].append((style, text))

    education_entries = _parse_dated_entries(sections.get("education", []))
    education = [
        {
            "institution": e["name"],
            "location": e["location"],
            "dates": e["dates"],
            "degree": e["detail"],
        }
        for e in education_entries
    ]

    job_entries = _parse_dated_entries(sections.get("experience", []))
    jobs = [
        {
            "company": e["name"],
            "location": e["location"],
            "dates": e["dates"],
            "title": e["detail"],
            "source_bullets": e["bullets"],
        }
        for e in job_entries
    ]

    if not jobs:
        sys.exit(
            f"Could not parse any employers out of the EXPERIENCE section of {resume_name}. "
            "Expected 'Company | Location <tab> Dates' header lines followed by a title line and "
            "bulleted List Paragraph entries."
        )

    return {"education": education, "jobs": jobs}


# ---------------------------------------------------------------------------
# LLM calls — a drafting call plus a JSON-transcription call, producing only
# the parts requiring judgment: the summary, per-employer bullets, and skills.
# ---------------------------------------------------------------------------

# Pipeline-specific I/O contract appended to the skill's methodology at call
# time. Kept here (not in the skill) because it's coupled to how this script
# parses the draft — company/dates/titles are filled in deterministically, and
# the "{company_block}" placeholder is substituted with the parsed employers.
PIPELINE_OUTPUT_CONTRACT = """

---

Pipeline I/O for this run: Company, location, date, and title fields are already fixed \
and handled separately, so do not repeat or alter them. Focus entirely on the summary, \
the bullets for each employer listed below (cover every one of them), and the skills \
list. Present your result as clear, readable text (plain text or markdown, your choice; \
a later step handles final structuring). Employers to cover, in order:
{company_block}"""

# Appended to the contract only when a fact bank is supplied.
CITATION_CONTRACT = """

Citations: end every experience bullet with the ids of the FACT BANK entries it is \
built from, in square brackets, e.g. "Led in-house marketing mix modeling, saving $300k \
per year. [F012, F031]". Cite only facts whose employer is that bullet's employer, or \
"general". Never cite an "unassigned" fact in a bullet. A later step validates and \
removes the brackets, so they never appear in the final resume. Do not cite in the \
summary or skills."""


def load_skill(path: Path) -> str:
    """Load a skill's instructional body, stripping the YAML frontmatter so it
    can be used verbatim as a system prompt. Skills are the single source of
    truth for judgment/writing rules."""
    if not path.exists():
        sys.exit(
            f"Skill not found at {path}. It holds the rules that drive generation; "
            "restore it before running."
        )
    text = path.read_text(encoding="utf-8")
    # Drop a leading "---\n ... \n---\n" YAML frontmatter block if present.
    text = re.sub(r"^﻿?---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    return text.strip()


def load_tailoring_rules() -> str:
    return load_skill(TAILORING_SKILL_PATH)

FORMAT_JSON_EXAMPLE = """{
  "summary": "2-4 sentence tailored summary.",
  "bullets_by_company": {
    "Company Name One": ["Bullet one. [F001]", "Bullet two. [F004, F009]"],
    "Company Name Two": ["Bullet one. [F012]"]
  },
  "skills": ["Skill One", "Skill Two"]
}"""

FORMAT_SYSTEM_PROMPT = """You are a text-to-JSON transcription tool with no other \
function — you do not evaluate, fact-check, edit, or comment on the content, you only \
reformat it. Transcribe the resume text you are given into exactly this JSON shape, \
using exactly these field names copied literally and exactly these company names as \
the "bullets_by_company" keys, wrapped in <RESUME_JSON> and </RESUME_JSON> tags, with \
absolutely nothing else anywhere in your reply — no markdown, no commentary, no notes. \
If bullets end with bracketed ids like "[F001, F004]", copy them exactly as written:
<RESUME_JSON>
""" + FORMAT_JSON_EXAMPLE + """
</RESUME_JSON>"""


def _find_claude_cli() -> str:
    claude_bin = shutil.which("claude")
    if not claude_bin:
        sys.exit(
            "Could not find the `claude` CLI on PATH. Install the Claude Code CLI "
            "and run `claude /login` to authenticate with your subscription."
        )
    return claude_bin


def _clean_subprocess_env() -> dict:
    # Strip inherited CLAUDE_*/ANTHROPIC_* vars (e.g. this script may itself be
    # run from inside a Claude Code session) so the child CLI call behaves like
    # a clean, standalone invocation rather than a nested session — otherwise
    # it starts narrating/asking follow-up questions like an interactive agent.
    # The one exception is ANTHROPIC_API_KEY, which the user set on purpose
    # (in .env or the app's Settings) to pay per use instead of using a login.
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.upper().startswith("CLAUDE") and not k.upper().startswith("ANTHROPIC")
    }
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        env["ANTHROPIC_API_KEY"] = key
    return env


def _invoke_claude(
    claude_bin: str,
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    effort: str | None = None,
) -> str:
    # Pass the system prompt via a file, not a CLI arg: the `claude` entry on
    # Windows is a .CMD shim run through cmd.exe, which caps the whole command
    # line at 8191 chars, so a long system prompt overflows it ("The command
    # line is too long."). --system-prompt-file has no such limit.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", encoding="utf-8", delete=False
    ) as sp_file:
        sp_file.write(system_prompt)
        sp_path = sp_file.name

    try:
        proc = subprocess.run(
            [
                claude_bin,
                "-p",
                "--output-format",
                "json",
                "--tools",
                "",
                "--model",
                model or MODEL,
                "--effort",
                effort or EFFORT,
                "--system-prompt-file",
                sp_path,
            ],
            input=user_message,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=_clean_subprocess_env(),
            cwd=tempfile.gettempdir(),  # avoid CLAUDE.md auto-discovery from this repo's cwd
            timeout=CLAUDE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        sys.exit(
            f"claude CLI did not respond within {CLAUDE_TIMEOUT}s. Re-run, or raise "
            "CLAUDE_TIMEOUT in .env."
        )
    finally:
        os.unlink(sp_path)

    if proc.returncode != 0:
        sys.exit(f"claude CLI exited with an error:\n{proc.stderr.strip()}")

    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        sys.exit(f"Could not parse claude CLI output as JSON ({exc}):\n{proc.stdout}")

    if envelope.get("is_error"):
        sys.exit(f"claude CLI reported an error: {envelope.get('result')}")

    return envelope.get("result", "")


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


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
    text = _strip_code_fence(match.group(1) if match else raw)
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


SKILLS_SECTION_HEADING_RE = re.compile(
    r"^(core competencies|skills|skills\s*&?\s*tools|technical\s+(skills|toolkit))\s*:?\s*$",
    re.IGNORECASE,
)


def _clean_heading_line(line: str) -> str:
    return re.sub(r"^#{1,6}\s*|\*+", "", line).strip().rstrip(":")


def _split_skill_items(text: str) -> list:
    """Split on the model's item separator, then on "," — but never split a
    comma that's inside parentheses, since skill names sometimes list
    examples in parens (e.g. "Uplift Modeling (CausalML, PyLift)"), which a
    naive comma-split would break apart. The separator varies by run ("|",
    "·", "•", ";"), so normalize them all to "|" first — otherwise an entire
    unsplit category collapses into one long "item" that then fails the
    length check in clean_skill_label() and the whole category is lost."""
    text = re.sub(r"\s*[·•;]\s*", "|", text)
    items = []
    for chunk in text.split("|"):
        depth = 0
        current = ""
        for ch in chunk:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            if ch == "," and depth == 0:
                items.append(current)
                current = ""
            else:
                current += ch
        items.append(current)
    return [i.strip() for i in items if i.strip()]


CATEGORY_LINE_RE = re.compile(r"^-?\s*\*\*([^*]+):\*\*\s*(.+)$")

_SKILL_SENTENCE_PREFIX_RE = re.compile(
    r"^(led|built|drove|designed|managed|developed|created|delivered|"
    r"positioned|foundational|proven|owns?|owned|deployed|engineered)\b",
    re.IGNORECASE,
)


def clean_skill_label(raw: str) -> str | None:
    """Backstop against a skill entry being a full sentence, project
    description, or duration/scope qualifier — e.g. "Team Leadership" is a
    skill, "Team Leadership (8+ years managing direct reports)" is not. The
    length limit is deliberately loose: the 1-3 word ideal is enforced as a
    rule of thumb in the prompt, and legitimate standard terms are sometimes
    longer (e.g. "Data Science End-to-End Project Facilitation"), so this only
    rejects entries long enough to clearly be prose. Strips an overly long
    trailing parenthetical and keeps the base label when possible, rather than
    discarding the whole entry."""
    label = raw.strip()

    match = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", label)
    if match:
        base, paren = match.group(1).strip(), match.group(2).strip()
        if len(paren) > 20 or re.search(r"\d", paren):
            label = base  # the parenthetical is an explanation, not a short qualifier

    # A tenure/duration reference ("8+ years managing...") is an achievement
    # claim, not a skill label — reject rather than try to salvage it.
    if re.search(r"\d+\+?\s*years?\b", label, re.IGNORECASE):
        return None

    # A dollar figure, a mid-sentence preposition ("... of a $1B+ multi-brand"),
    # or a numeric scope qualifier ("... teams of 12+") signals a fragment cut
    # out of a longer sentence, not a clean label — these can still be short
    # enough to pass the length check.
    if "$" in label or re.search(
        r"\b(of|for|with)\s+(a|the)\b|\bof\s+\d", label, re.IGNORECASE
    ):
        return None

    if not label or len(label.split()) > 7 or len(label) > 55:
        return None
    if _SKILL_SENTENCE_PREFIX_RE.match(label):
        return None
    return label


def extract_skills_from_draft(draft: str) -> list:
    """Deterministically pull every skill/tool out of the draft's
    competencies section — the JSON-transcription step doesn't reliably
    flatten this. Primarily detects the categorized layout ("**Category:**
    item | item", optionally bulleted) structurally, wherever it appears,
    since the model uses a different heading each run ("CORE COMPETENCIES",
    "CORE STRENGTHS", ...) rather than matching on heading text. Falls back
    to a heading-based search for a flat, uncategorized list. Every candidate
    item is passed through clean_skill_label() as a backstop against verbose,
    sentence-like entries slipping through despite the prompt instruction."""
    lines = draft.splitlines()

    items = []
    for line in lines:
        match = CATEGORY_LINE_RE.match(line.strip())
        if match:
            for raw in _split_skill_items(match.group(2)):
                cleaned = clean_skill_label(raw)
                if cleaned:
                    items.append(cleaned)
    if items:
        return items

    start = None
    for i, line in enumerate(lines):
        if SKILLS_SECTION_HEADING_RE.match(_clean_heading_line(line)):
            start = i + 1
            break
    if start is None:
        return []

    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^#{1,6}\s+\S", stripped) or re.match(r"^-{3,}$", stripped):
            break  # next section heading or a horizontal-rule divider
        content = re.sub(r"^[-*]\s+", "", stripped)  # drop a bullet marker, if any
        for raw in _split_skill_items(content):
            cleaned = clean_skill_label(raw)
            if cleaned:
                items.append(cleaned)
    return items


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
    claude_bin = _find_claude_cli()
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
    draft = _invoke_claude(claude_bin, draft_system_prompt, user_message, model, effort)

    stage("structuring")
    print("  Converting to structured data...")
    parsed = None
    raw = ""
    for attempt in range(3):
        raw = _invoke_claude(claude_bin, FORMAT_SYSTEM_PROMPT, draft, model, effort)
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


# ---------------------------------------------------------------------------
# Deterministic validation/correction guards — cheap, precise checks that
# don't depend on LLM self-compliance.
# ---------------------------------------------------------------------------

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


def _company_keywords(name: str) -> list:
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
            (other, kw) for other in companies if other != company for kw in _company_keywords(other)
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

    claude_bin = _find_claude_cli()
    system_prompt = load_skill(COVER_LETTER_SKILL_PATH)
    raw = ""
    for attempt in range(3):
        raw = _invoke_claude(claude_bin, system_prompt, user_message, model, effort)
        match = re.search(r"<COVER_LETTER>(.*?)</COVER_LETTER>", raw, re.DOTALL)
        body = _strip_code_fence(match.group(1) if match else raw)
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


def remove_em_dashes(text: str) -> str:
    """Backstop for the "no em dashes" style rule — prompt compliance isn't
    guaranteed, so replace any that slip through with a comma (safe for the
    fragment-style clauses resume bullets/summaries use)."""
    text = re.sub(r"\s*—\s*", ", ", text)
    # A spaced en dash (" – ") is the same tell; an unspaced one ("2019–2021")
    # is a range and stays.
    text = re.sub(r"\s+–\s+", ", ", text)
    return re.sub(r",\s*,", ",", text)


def _skill_key(skill: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", skill).strip().lower()


def parse_profile_skills(profile) -> dict:
    """Deterministically pull the flat skill/tool lists out of the profile's
    'Software/Tools' and 'Skills' sections (List Paragraph entries under those
    headers) — used as a truthful pool to backfill anything the model omits.
    Kept separate: tool names are unambiguous and safe to always list in full;
    the broader skills phrases benefit more from job-specific filtering."""
    paras, _ = _paras_and_name(profile)

    tool_section_names = {"software/tools", "software / tools", "tools"}
    skill_section_names = {"skills"}
    tools, skills = [], []
    current = None
    for style, text in paras:
        key = text.rstrip(":").strip().lower()
        if style == "Normal":
            if key in tool_section_names:
                current = tools
            elif key in skill_section_names:
                current = skills
            else:
                current = None
            continue
        if current is not None and style == "List Paragraph":
            current.append(text)
    return {"tools": tools, "skills": skills}


def merge_and_sort_skills(tailored_skills: list, profile_skills: dict, job_text: str) -> list:
    """The model curates the actual skills list (mix of tools, soft skills,
    frameworks, and DS subfields, picked for relevance to this posting). This
    is just a narrow safety net: force-include a profile tool/skill only when
    the job posting itself explicitly names it too (e.g. "Python" shouldn't
    be missing when both the profile and the posting mention it) — it doesn't
    dump the whole profile in, which would fight the model's curation. Merge,
    dedup, and sort alphabetically."""
    job_lower = job_text.lower()
    must_include = [
        s
        for s in profile_skills["tools"] + profile_skills["skills"]
        if _skill_key(s) and _skill_key(s) in job_lower
    ]

    seen = {}
    for skill in tailored_skills + must_include:
        key = _skill_key(skill)
        if key and key not in seen:
            seen[key] = skill
    return sorted(seen.values(), key=str.lower)


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
        key = _skill_key(term)
        if len(key) >= 2 and key not in vocab:
            vocab[key] = term.strip()

    job_lower, out_lower = job_text.lower(), output_text.lower()
    covered, missing = [], []
    for key, term in sorted(vocab.items()):
        if not _contains_term(key, job_lower):
            continue
        (covered if _contains_term(key, out_lower) else missing).append(term)
    return covered, missing


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


# ---------------------------------------------------------------------------
# Assembly + docx/pdf output.
# ---------------------------------------------------------------------------


def slugify_name(first: str, last: str) -> str:
    def clean(part: str) -> str:
        part = part.strip().lower()
        part = re.sub(r"[^a-z0-9]+", "-", part)
        return part.strip("-")

    return f"{clean(first)}-{clean(last)}"


def _set_bottom_border(paragraph, color: str = RULE_COLOR, size: int = 6) -> None:
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_hyperlink(paragraph, text: str, url: str) -> None:
    """Append a clickable external link (python-docx has no API for this).
    Styled like the surrounding contact text so it doesn't read as blue link
    text; ATS parsers and PDF viewers still pick up the target."""
    r_id = paragraph.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    run_text = OxmlElement("w:t")
    run_text.text = text
    run_text.set(qn("xml:space"), "preserve")
    run.append(run_text)
    link.append(run)
    paragraph._p.append(link)


@dataclass(frozen=True)
class TemplateSpec:
    """Everything that differs between the resume templates. All of them stay
    inside the ATS-safe envelope from resume_best_practices.md: one column,
    no tables, nothing in the header/footer layer, a standard font."""

    key: str
    label: str
    description: str
    font: str = "Calibri"
    body_size: float = 10.5
    name_size: float = 22
    contact_size: float = 9.5
    section_size: float = 11.5
    entry_title_size: float = 10
    ink: RGBColor = INK  # name and section headings
    accent: RGBColor = INK  # company line in title-first layouts
    muted: RGBColor = MUTED
    rule_color: str | None = RULE_COLOR  # section heading underline; None for none
    rule_size: int = 6
    margin_tb: float = 0.55
    margin_lr: float = 0.75
    name_align: str = "center"
    name_small_caps: bool = False
    section_all_caps: bool = True
    section_small_caps: bool = False
    section_space_before: float = 12
    section_space_after: float = 4
    body_space_after: float = 4
    bullet_space_after: float = 3
    bullet_indent: float = 0.2
    job_space_after: float = 8
    contact_space_after: float = 10
    # "company_first": Company | Location + dates, then an italic title line.
    # "title_first": bold title + dates, then Company | Location in the accent color.
    entry_layout: str = "company_first"
    skills_separator: str = ", "


TEMPLATES = {
    "classic": TemplateSpec(
        key="classic",
        label="Classic",
        description="Centered navy header and ruled section headings. The original design.",
    ),
    "modern": TemplateSpec(
        key="modern",
        label="Modern",
        description="Left-aligned header with a teal accent, role titles leading each entry.",
        font="Arial",
        body_size=10,
        name_size=24,
        contact_size=9,
        section_size=11,
        entry_title_size=10,
        ink=RGBColor(0x0F, 0x5E, 0x63),
        accent=RGBColor(0x0F, 0x5E, 0x63),
        muted=RGBColor(0x55, 0x5B, 0x66),
        rule_color="C9D3D6",
        rule_size=4,
        margin_tb=0.6,
        margin_lr=0.7,
        name_align="left",
        section_all_caps=False,
        section_space_before=11,
        contact_space_after=8,
        entry_layout="title_first",
        skills_separator=" | ",
    ),
    "compact": TemplateSpec(
        key="compact",
        label="Compact",
        description="Serif, tighter margins and spacing. Fits a long career on fewer pages.",
        font="Cambria",
        body_size=10,
        name_size=18,
        contact_size=9,
        section_size=10.5,
        entry_title_size=9.5,
        ink=RGBColor(0x1A, 0x1A, 0x1A),
        accent=RGBColor(0x1A, 0x1A, 0x1A),
        muted=RGBColor(0x4A, 0x4A, 0x4A),
        rule_color="1A1A1A",
        rule_size=4,
        margin_tb=0.5,
        margin_lr=0.6,
        name_small_caps=True,
        section_all_caps=False,
        section_small_caps=True,
        section_space_before=8,
        section_space_after=3,
        body_space_after=2,
        bullet_space_after=1.5,
        bullet_indent=0.18,
        job_space_after=5,
        contact_space_after=6,
        skills_separator=" | ",
    ),
}
DEFAULT_TEMPLATE = "classic"


def get_template(key: str | None) -> TemplateSpec:
    return TEMPLATES.get(key or DEFAULT_TEMPLATE, TEMPLATES[DEFAULT_TEMPLATE])


def _build_styles(d: docx.Document, spec: TemplateSpec) -> dict:
    styles = d.styles

    normal = styles["Normal"]
    normal.font.name = spec.font
    normal.font.size = Pt(spec.body_size)
    normal.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(spec.body_space_after)
    normal.paragraph_format.line_spacing = 1.0

    align = WD_ALIGN_PARAGRAPH.CENTER if spec.name_align == "center" else WD_ALIGN_PARAGRAPH.LEFT

    name_style = styles.add_style("ResumeName", WD_STYLE_TYPE.PARAGRAPH)
    name_style.base_style = normal
    name_style.font.size = Pt(spec.name_size)
    name_style.font.bold = True
    name_style.font.small_caps = spec.name_small_caps or None
    name_style.font.color.rgb = spec.ink
    name_style.paragraph_format.alignment = align
    name_style.paragraph_format.space_after = Pt(2)

    contact_style = styles.add_style("ResumeContact", WD_STYLE_TYPE.PARAGRAPH)
    contact_style.base_style = normal
    contact_style.font.size = Pt(spec.contact_size)
    contact_style.font.color.rgb = spec.muted
    contact_style.paragraph_format.alignment = align
    contact_style.paragraph_format.space_after = Pt(spec.contact_space_after)

    section_style = styles.add_style("ResumeSection", WD_STYLE_TYPE.PARAGRAPH)
    section_style.base_style = normal
    section_style.font.size = Pt(spec.section_size)
    section_style.font.bold = True
    section_style.font.color.rgb = spec.ink
    section_style.font.all_caps = spec.section_all_caps or None
    section_style.font.small_caps = spec.section_small_caps or None
    section_style.paragraph_format.space_before = Pt(spec.section_space_before)
    section_style.paragraph_format.space_after = Pt(spec.section_space_after)

    entry_title_style = styles.add_style("ResumeEntryTitle", WD_STYLE_TYPE.PARAGRAPH)
    entry_title_style.base_style = normal
    entry_title_style.font.italic = True
    entry_title_style.font.size = Pt(spec.entry_title_size)
    entry_title_style.font.color.rgb = spec.muted
    entry_title_style.paragraph_format.space_after = Pt(3 if spec.body_space_after >= 4 else 1.5)

    bullet_style = styles["List Bullet"]
    bullet_style.font.name = spec.font
    bullet_style.font.size = Pt(spec.body_size)  # match body text in Summary/Education/Skills
    bullet_style.paragraph_format.left_indent = Inches(spec.bullet_indent)
    bullet_style.paragraph_format.space_after = Pt(spec.bullet_space_after)
    bullet_style.paragraph_format.line_spacing = 1.0

    return {"section": section_style, "entry_title": entry_title_style}


def _add_entry_header(d: docx.Document, left_text: str, right_text: str, spec: TemplateSpec | None = None):
    spec = spec or TEMPLATES[DEFAULT_TEMPLATE]
    p = d.add_paragraph()
    content_width = (
        d.sections[0].page_width - d.sections[0].left_margin - d.sections[0].right_margin
    )
    p.paragraph_format.tab_stops.add_tab_stop(content_width, WD_TAB_ALIGNMENT.RIGHT)
    left_run = p.add_run(left_text)
    left_run.bold = True
    if right_text:
        right_run = p.add_run(f"\t{right_text}")
        right_run.font.color.rgb = spec.muted
    p.paragraph_format.space_after = Pt(1)
    return p


def _new_document(data: dict, spec: TemplateSpec | None = None) -> tuple:
    """Letter-size document with the shared styles and the name/contact
    header, used by both the resume and the cover letter."""
    spec = spec or TEMPLATES[DEFAULT_TEMPLATE]
    d = docx.Document()

    section = d.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(spec.margin_tb)
    section.bottom_margin = Inches(spec.margin_tb)
    section.left_margin = Inches(spec.margin_lr)
    section.right_margin = Inches(spec.margin_lr)

    styles = _build_styles(d, spec)

    d.add_paragraph(f"{data['first_name']} {data['last_name']}", style="ResumeName")
    contact_p = d.add_paragraph(style="ResumeContact")
    linkedin = data.get("linkedin", "")
    parts = [
        (data["email"], f"mailto:{data['email']}" if data["email"] else None),
        (data["phone"], None),
        (data["location"], None),
        (linkedin, linkedin if linkedin.lower().startswith("http") else f"https://{linkedin}"),
    ]
    first = True
    for text, url in parts:
        if not text:
            continue
        if not first:
            contact_p.add_run(" | ")
        first = False
        if url:
            _add_hyperlink(contact_p, text, url)
        else:
            contact_p.add_run(text)
    return d, styles


def build_cover_letter_docx(data: dict, paragraphs: list, out_path: Path, template: str | None = None) -> None:
    d, _styles = _new_document(data, get_template(template))
    d.add_paragraph(datetime.now().strftime("%B %d, %Y").replace(" 0", " "))
    d.add_paragraph("Dear Hiring Team,")
    for text in paragraphs:
        d.add_paragraph(text).paragraph_format.space_after = Pt(8)
    d.add_paragraph("Sincerely,")
    d.add_paragraph(f"{data['first_name']} {data['last_name']}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(out_path))


def build_docx(data: dict, out_path: Path, template: str | None = None) -> None:
    spec = get_template(template)
    d, styles = _new_document(data, spec)

    def add_heading(text: str) -> None:
        p = d.add_paragraph(text, style=styles["section"])
        if spec.rule_color:
            _set_bottom_border(p, spec.rule_color, spec.rule_size)

    add_heading("Summary")
    d.add_paragraph(data["summary"])

    if data.get("education"):
        add_heading("Education")
        for edu in data["education"]:
            header = " | ".join(
                part for part in (edu.get("institution"), edu.get("location")) if part
            )
            _add_entry_header(d, header, edu.get("dates", ""), spec)
            degree_p = d.add_paragraph(edu.get("degree", ""))
            degree_p.paragraph_format.space_after = Pt(6 if spec.body_space_after >= 4 else 3)

    if data.get("experience"):
        add_heading("Experience")
        for job in data["experience"]:
            place = " | ".join(part for part in (job.get("company"), job.get("location")) if part)
            if spec.entry_layout == "title_first":
                _add_entry_header(d, job.get("title", "") or place, job.get("dates", ""), spec)
                company_p = d.add_paragraph()
                company_run = company_p.add_run(place)
                company_run.font.color.rgb = spec.accent
                company_run.bold = True
                company_run.font.size = Pt(spec.entry_title_size)
                company_p.paragraph_format.space_after = Pt(3)
            else:
                _add_entry_header(d, place, job.get("dates", ""), spec)
                d.add_paragraph(job.get("title", ""), style=styles["entry_title"])
            bullets = job.get("bullets", [])
            for i, bullet in enumerate(bullets):
                p = d.add_paragraph(bullet, style="List Bullet")
                if i == len(bullets) - 1:
                    p.paragraph_format.space_after = Pt(spec.job_space_after)

    if data.get("skills"):
        add_heading("Skills")
        d.add_paragraph(spec.skills_separator.join(data["skills"]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(out_path))


def _convert_with_word(docx_path: Path, pdf_path: Path) -> None:
    """Export through Word's COM API directly. docx2pdf does the same, but it
    reuses any Word window you have open, prints progress bars, and treats
    Word dropping the COM link on Quit() (common, and harmless once the PDF
    exists) as a failure. A private DispatchEx instance avoids all three."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(docx_path.resolve()), ReadOnly=True, AddToRecentFiles=False)
        try:
            doc.ExportAsFixedFormat(str(pdf_path.resolve()), 17)  # 17 = wdExportFormatPDF
        finally:
            doc.Close(False)
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def convert_to_pdf(docx_path: Path, pdf_path: Path) -> None:
    if pdf_path.exists():
        pdf_path.unlink()
    if sys.platform == "win32":
        _convert_with_word(docx_path, pdf_path)
    else:
        from docx2pdf import convert

        convert(str(docx_path), str(pdf_path))
    if not pdf_path.exists():
        raise RuntimeError("Word finished without producing a PDF")


OUTPUT_PREFIXES = ("out_resume_", "out_cover_letter_")


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def archive_existing_outputs(create_dir: Path | None = None, archive_dir: Path | None = None) -> None:
    create_dir = create_dir or CREATE_DIR
    archive_dir = archive_dir or ARCHIVE_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)
    create_dir.mkdir(parents=True, exist_ok=True)

    archive_time = datetime.now().strftime("%H-%M-%S")
    for prefix in OUTPUT_PREFIXES:
        for docx_file in create_dir.glob(f"{prefix}*.docx"):
            archived_name = f"{docx_file.stem}-{archive_time}{docx_file.suffix}"
            shutil.move(str(docx_file), str(archive_dir / archived_name))
            print(f"Archived {docx_file.name} -> {archive_dir.name}/{archived_name}")

        for report_file in create_dir.glob(f"{prefix}*_report.md"):
            base = report_file.name[: -len("_report.md")]
            archived_name = f"{base}-{archive_time}_report.md"
            shutil.move(str(report_file), str(archive_dir / archived_name))
            print(f"Archived {report_file.name} -> {archive_dir.name}/{archived_name}")

        for pdf_file in create_dir.glob(f"{prefix}*.pdf"):
            pdf_file.unlink()
            print(f"Removed superseded {pdf_file.name} (only .docx versions are archived)")


# ---------------------------------------------------------------------------
# Result JSON: the structured, editable form of one run. Written with
# --result-json, re-rendered (no LLM) with --render-json. Resume Taylor keeps
# one per project so hand edits and template switches never need a new draft.
# ---------------------------------------------------------------------------

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


def write_outputs(
    result: dict,
    out_dir: Path,
    archive_dir: Path | None,
    template: str,
    no_pdf: bool,
    fact_bank: dict | None = None,
) -> Path:
    """Archive whatever is in out_dir, then write the resume (and cover letter)
    .docx/.pdf plus the tailoring report. Returns the report path."""
    data = result_to_docx_data(result)
    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify_name(data["first_name"], data["last_name"])
    base_name = f"out_resume_{slug}_{today}"
    cl_base_name = f"out_cover_letter_{slug}_{today}"
    page_count = None

    archive_existing_outputs(out_dir, archive_dir)
    stage("rendering")
    outputs = [(base_name, lambda path: build_docx(data, path, template))]
    if result.get("cover_letter"):
        paragraphs = [p["text"] for p in result["cover_letter"]]
        outputs.append((cl_base_name, lambda path: build_cover_letter_docx(data, paragraphs, path, template)))
    for name, build in outputs:
        docx_path = out_dir / f"{name}.docx"
        pdf_path = out_dir / f"{name}.pdf"
        build(docx_path)
        print(f"Wrote {_display(docx_path)}")
        if no_pdf:
            continue
        stage("pdf")
        try:
            convert_to_pdf(docx_path, pdf_path)
            print(f"Wrote {_display(pdf_path)}")
        except Exception as exc:  # docx2pdf requires MS Word via COM automation
            warn(f"could not generate {pdf_path.name} ({exc}). The .docx was still created.")
            continue
        pages = count_pdf_pages(pdf_path)
        if name == base_name:
            page_count = pages
            print(f"Resume length: {pages} page(s)")
            if pages > 2:
                warn(f"the resume runs {pages} pages; consider cutting the weakest bullets.")
        elif pages > 1:
            warn(f"the cover letter runs {pages} pages; it should fit on one.")

    result["page_count"] = page_count
    result["template"] = template
    report_path = out_dir / f"{base_name}_report.md"
    coverage = result.get("coverage") or {}
    write_report(
        report_path,
        result.get("inputs") or {},
        result.get("model", MODEL),
        result.get("effort", EFFORT),
        WARNINGS,
        (coverage.get("covered", []), coverage.get("missing", [])),
        result_bullets_by_company(result),
        result_citations(result),
        fact_bank,
        result.get("draft", ""),
        cover_letter=[(p["text"], p.get("ids") or []) for p in result.get("cover_letter") or []] or None,
        page_count=page_count,
    )
    return report_path


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a resume tailored to one job posting.")
    parser.add_argument(
        "--job",
        type=Path,
        help="job posting .docx/.pdf/.txt/.md (default: newest resume_input/in_job*)",
    )
    parser.add_argument("--profile", type=Path, help="profile .docx (default: newest resume_input/in_profile*)")
    parser.add_argument("--resume", type=Path, help="prior resume .docx (default: newest resume_input/in_resume*)")
    parser.add_argument(
        "--fact-bank", type=Path, help=f"fact bank YAML (default: {FACT_BANK_PATH.relative_to(ROOT)})"
    )
    parser.add_argument("--deny", type=Path, help=f"never-claim list (default: {DO_NOT_CLAIM_PATH.name}, else the starter {DO_NOT_CLAIM_EXAMPLE.name})")
    parser.add_argument(
        "--cover-letter",
        action="store_true",
        help="also write a cover letter built from the validated resume content",
    )
    parser.add_argument(
        "--archive-job",
        action="store_true",
        help="after a successful run, move the job posting into resume_archive/",
    )
    parser.add_argument("--model", default=MODEL, help=f"Claude model (default: {MODEL})")
    parser.add_argument("--effort", default=EFFORT, help=f"reasoning effort (default: {EFFORT})")
    parser.add_argument(
        "--template",
        choices=sorted(TEMPLATES),
        default=DEFAULT_TEMPLATE,
        help=f"resume layout (default: {DEFAULT_TEMPLATE})",
    )
    parser.add_argument("--out-dir", type=Path, help="where to write outputs (default: resume_create/)")
    parser.add_argument("--archive-dir", type=Path, help="where superseded outputs go (default: resume_archive/)")
    parser.add_argument("--result-json", type=Path, help="also save the structured, editable result here")
    parser.add_argument(
        "--render-json",
        type=Path,
        help="skip generation: re-validate and render a saved result JSON (no Claude call)",
    )
    parser.add_argument("--no-pdf", action="store_true", help="skip the Word-based PDF export")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run generation and validation, print the result and a report, but archive/write nothing",
    )
    return parser.parse_args(argv)


def _require(path: Path, what: str) -> Path:
    if not path.exists():
        sys.exit(f"{what} not found: {path}")
    return path


def load_context(args: argparse.Namespace) -> dict:
    """Locate and parse every input. Shared by generation and --render-json."""
    profile_path = _require(args.profile or find_latest("in_profile"), "Profile")
    resume_path = _require(args.resume or find_latest("in_resume"), "Prior resume")
    job_path = _require(args.job or find_latest("in_job", JOB_POSTING_EXTS), "Job posting")
    deny_path = args.deny or DO_NOT_CLAIM_PATH

    print(f"Profile: {profile_path.name}")
    print(f"Prior resume: {resume_path.name}")
    print(f"Job posting: {job_path.name}")

    contact = parse_applicant_info(profile_path)
    parsed_resume = parse_prior_resume(resume_path)
    companies = [job["company"] for job in parsed_resume["jobs"]]
    profile_text = read_docx_text(profile_path)
    resume_text = read_docx_text(resume_path)
    job_text = read_input_text(job_path)
    if not job_text:
        sys.exit(f"No text could be read from {job_path.name} (a scanned PDF?). Save it as .txt instead.")

    return {
        "profile_path": profile_path,
        "resume_path": resume_path,
        "job_path": job_path,
        "contact": contact,
        "parsed_resume": parsed_resume,
        "companies": companies,
        "profile_text": profile_text,
        "resume_text": resume_text,
        "job_text": job_text,
        "source_text": profile_text + "\n" + resume_text,
        "deny_patterns": load_deny_patterns(deny_path),
        "deny_name": deny_path.name,
        "fact_bank_path": args.fact_bank or FACT_BANK_PATH,
        "profile_skills": parse_profile_skills(profile_path),
        "inputs": {
            "Profile": profile_path.name,
            "Prior resume": resume_path.name,
            "Job posting": job_path.name,
        },
    }


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


def main(argv=None) -> None:
    args = parse_args(argv)
    WARNINGS.clear()
    stage("preparing")

    ctx = load_context(args)
    ctx["fact_bank"] = load_fact_bank(ctx["companies"], ctx["fact_bank_path"])
    if args.render_json:
        print(f"Re-rendering {args.render_json.name} (no Claude call)...")
    elif ctx["fact_bank"]:
        print(f"Fact bank: {len(ctx['fact_bank'])} facts (citations enforced)")
    else:
        print(
            f"Fact bank: none at {_display(ctx['fact_bank_path'])}; bullets won't be "
            "provenance-checked. Run `python build_fact_bank.py` to create one."
        )

    if args.render_json:
        result = load_result(args.render_json)
        stage("validating")
        revalidate_result(result, ctx)
    else:
        result = generate(args, ctx)
        result["generation_warnings"] = list(WARNINGS)

    out_dir = args.out_dir or CREATE_DIR
    if args.dry_run:
        print(f"\n--- DRY RUN: nothing archived or written to {out_dir.name}/ ---\n")
        print(f"SUMMARY\n{result['summary']}\n")
        for job in result["experience"]:
            print(job["company"])
            for bullet in job["bullets"]:
                print(f"  - {bullet['text']}")
        print(f"\nSKILLS\n{', '.join(result['skills'])}\n")
        if result.get("cover_letter"):
            print("COVER LETTER\n" + "\n\n".join(p["text"] for p in result["cover_letter"]) + "\n")
        base = f"out_resume_{slugify_name(result['contact']['first_name'], result['contact']['last_name'])}"
        report_path = Path(tempfile.gettempdir()) / f"{base}_{datetime.now():%Y-%m-%d}_report.md"
        coverage = result.get("coverage") or {}
        write_report(
            report_path,
            result["inputs"],
            result.get("model", args.model),
            result.get("effort", args.effort),
            WARNINGS,
            (coverage.get("covered", []), coverage.get("missing", [])),
            result_bullets_by_company(result),
            result_citations(result),
            ctx["fact_bank"],
            result.get("draft", ""),
            cover_letter=[(p["text"], p["ids"]) for p in result.get("cover_letter") or []] or None,
        )
    else:
        report_path = write_outputs(
            result, out_dir, args.archive_dir, args.template, args.no_pdf, ctx["fact_bank"]
        )
        if args.archive_job and not args.render_json:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(str(ctx["job_path"]), str(ARCHIVE_DIR / ctx["job_path"].name))
            print(f"Archived job posting {ctx['job_path'].name} -> resume_archive/")

    result["warnings"] = list(WARNINGS)
    if args.result_json:
        save_result(result, args.result_json)
        print(f"Saved result to {_display(args.result_json)}")
    stage("done")
    print(f"{len(WARNINGS)} warning(s); see {report_path}")


if __name__ == "__main__":
    main()
