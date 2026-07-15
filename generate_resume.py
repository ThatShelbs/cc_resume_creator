"""
Generate a tailored resume from the files in resume_input/.

Reads the applicant profile, a prior example resume, and a target job posting
(all .docx), asks the Anthropic API to select and reword only *true* content
from the profile/prior resume to fit the job posting, then writes the result
to resume_create/ as .docx + .pdf. Any resume already in resume_create/ is
moved to resume_archive/ (.docx only) before the new one is written.

Usage:
    python generate_resume.py
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import docx
from anthropic import Anthropic
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from dotenv import load_dotenv

INK = RGBColor(0x1F, 0x2A, 0x44)
MUTED = RGBColor(0x44, 0x44, 0x44)
RULE_COLOR = "1F2A44"

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "resume_input"
CREATE_DIR = ROOT / "resume_create"
ARCHIVE_DIR = ROOT / "resume_archive"

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

RESUME_SCHEMA = {
    "name": "emit_resume",
    "description": "The finished, tailored resume content.",
    "input_schema": {
        "type": "object",
        "properties": {
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
            "email": {"type": "string"},
            "phone": {"type": "string"},
            "location": {"type": "string"},
            "summary": {
                "type": "string",
                "description": "2-4 sentence professional summary tailored to the job posting.",
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "institution": {"type": "string"},
                        "location": {"type": "string"},
                        "dates": {"type": "string"},
                        "degree": {"type": "string"},
                    },
                    "required": ["institution", "dates", "degree"],
                },
            },
            "experience": {
                "type": "array",
                "description": "Employment history, most recent first. Companies, titles, and dates must exactly match the source resume.",
                "items": {
                    "type": "object",
                    "properties": {
                        "company": {"type": "string"},
                        "location": {"type": "string"},
                        "dates": {"type": "string"},
                        "title": {"type": "string"},
                        "bullets": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["company", "dates", "title", "bullets"],
                },
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Flat list of skills/tools relevant to the target role.",
            },
        },
        "required": [
            "first_name",
            "last_name",
            "email",
            "phone",
            "location",
            "summary",
            "education",
            "experience",
            "skills",
        ],
    },
}

SYSTEM_PROMPT = """You are an expert resume strategist. Your job is to make a candidate's \
truthful, existing career history land as strongly as possible for ONE specific job \
posting, so a recruiter reading it decides to call the candidate for a screening or \
interview. Tailoring to the posting is the main thing you are being judged on — a \
resume that just restates the source documents in the original order is a failure, \
even if every fact in it is true.

Ground truth, non-negotiable:
- Every employer, title, and date must come exactly from the "PRIOR RESUME" document. \
Do not add, remove, reorder, merge, split, or alter employers/titles/dates.
- Every accomplishment, metric, and skill you use must already exist in the PROFILE \
and/or PRIOR RESUME documents. Never invent, exaggerate, or imply experience, tools, \
metrics, or scope the candidate doesn't have. If the posting wants something the \
candidate has never done, do not claim it and do not imply it through word choice \
(e.g. don't call real attribution-modeling work "incrementality testing" unless the \
source material actually describes incrementality testing).
- Do not stretch the truth or put the applicant "over their skis" — tailoring means \
selection, reordering, and honest reframing of real experience, never fabrication.
- Never transplant a detail, scope claim, or outcome from one employer's true bullet \
onto a different employer's bullet, even if it sounds plausible for both. Never add a \
scope, audience, or downstream-impact claim (e.g. who a result "informed" or was \
"used by") beyond what the source material states for that specific accomplishment.
- Every bullet listed under an employer must describe work done at that employer only. \
Never mention a different employer, or that employer's outcome, inside another \
employer's bullet — not even as a "previously did X at Y" aside. If an accomplishment \
belongs to Employer A, it goes only under Employer A's bullets.

Tailoring — weight this heavily:
- Before writing anything, identify the 5-8 things this specific posting most cares \
about (its "You Will" / "You Have" priorities, its named responsibilities, its own \
vocabulary).
- For each employer, pull from every TRUE bullet available across PROFILE and PRIOR \
RESUME for that employer (the profile often has more detail/metrics than the old \
resume's bullets) and select the ones that most directly serve this posting's \
priorities. Prefer fewer, sharper, highly relevant bullets over reproducing the \
source's full list — aim for roughly 3-5 strong bullets per role, cutting or shrinking \
whatever doesn't support this posting, and lead each role with its most relevant bullet.
- Reword bullets in the posting's own vocabulary wherever that vocabulary accurately \
describes what the candidate truly did. Quantify impact whenever the source material \
has a number.
- Order the skills list so the skills this posting explicitly names come first; still \
only include skills present in the source documents.
- Write the summary as a direct, confident pitch for this exact role: open with the \
candidate's single strongest true qualification against the posting's top priority, \
and use the posting's own framing (its title, its named priorities) wherever that \
framing is honestly supported by the source material.
- Output only by calling the emit_resume tool. No other commentary."""


def read_docx_text(path: Path) -> str:
    d = docx.Document(str(path))
    lines = [p.text for p in d.paragraphs if p.text.strip()]
    for table in d.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def find_latest(prefix: str) -> Path:
    matches = sorted(INPUT_DIR.glob(f"{prefix}*.docx"))
    if not matches:
        sys.exit(
            f"No file starting with '{prefix}' found in {INPUT_DIR}. "
            f"Expected a profile, prior resume, and job posting (in_profile*, "
            f"in_resume*, in_job*)."
        )
    return matches[-1]


def call_llm(profile_text: str, resume_text: str, job_text: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(
            "ANTHROPIC_API_KEY is not set. Add it to a .env file in the repo root "
            "(see .env.example) or export it in your shell."
        )
    client = Anthropic(api_key=api_key)

    user_message = f"""PROFILE (source of truth for accomplishments, skills, and details):
{profile_text}

PRIOR RESUME (source of truth for employers, titles, and dates):
{resume_text}

JOB POSTING (tailor emphasis, ordering, and phrasing to this):
{job_text}

Produce the tailored resume by calling emit_resume."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        tools=[RESUME_SCHEMA],
        tool_choice={"type": "tool", "name": "emit_resume"},
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "emit_resume":
            return block.input

    sys.exit("Anthropic API response did not include the expected tool call.")


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


def _build_styles(d: docx.Document) -> dict:
    styles = d.styles

    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.0

    name_style = styles.add_style("ResumeName", WD_STYLE_TYPE.PARAGRAPH)
    name_style.base_style = normal
    name_style.font.size = Pt(22)
    name_style.font.bold = True
    name_style.font.color.rgb = INK
    name_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_style.paragraph_format.space_after = Pt(2)

    contact_style = styles.add_style("ResumeContact", WD_STYLE_TYPE.PARAGRAPH)
    contact_style.base_style = normal
    contact_style.font.size = Pt(9.5)
    contact_style.font.color.rgb = MUTED
    contact_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    contact_style.paragraph_format.space_after = Pt(10)

    section_style = styles.add_style("ResumeSection", WD_STYLE_TYPE.PARAGRAPH)
    section_style.base_style = normal
    section_style.font.size = Pt(11.5)
    section_style.font.bold = True
    section_style.font.color.rgb = INK
    section_style.font.all_caps = True
    section_style.paragraph_format.space_before = Pt(12)
    section_style.paragraph_format.space_after = Pt(4)

    entry_title_style = styles.add_style("ResumeEntryTitle", WD_STYLE_TYPE.PARAGRAPH)
    entry_title_style.base_style = normal
    entry_title_style.font.italic = True
    entry_title_style.font.size = Pt(10)
    entry_title_style.font.color.rgb = MUTED
    entry_title_style.paragraph_format.space_after = Pt(3)

    bullet_style = styles["List Bullet"]
    bullet_style.font.name = "Calibri"
    bullet_style.font.size = Pt(10)
    bullet_style.paragraph_format.left_indent = Inches(0.2)
    bullet_style.paragraph_format.space_after = Pt(3)
    bullet_style.paragraph_format.line_spacing = 1.0

    return {"section": section_style, "entry_title": entry_title_style}


def _add_entry_header(d: docx.Document, left_text: str, right_text: str):
    p = d.add_paragraph()
    content_width = (
        d.sections[0].page_width - d.sections[0].left_margin - d.sections[0].right_margin
    )
    p.paragraph_format.tab_stops.add_tab_stop(content_width, WD_TAB_ALIGNMENT.RIGHT)
    left_run = p.add_run(left_text)
    left_run.bold = True
    if right_text:
        right_run = p.add_run(f"\t{right_text}")
        right_run.font.color.rgb = MUTED
    p.paragraph_format.space_after = Pt(1)
    return p


def build_docx(data: dict, out_path: Path) -> None:
    d = docx.Document()

    section = d.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    styles = _build_styles(d)

    d.add_paragraph(f"{data['first_name']} {data['last_name']}", style="ResumeName")
    d.add_paragraph(
        " | ".join(
            part for part in (data["email"], data["phone"], data["location"]) if part
        ),
        style="ResumeContact",
    )

    def add_heading(text: str) -> None:
        p = d.add_paragraph(text, style=styles["section"])
        _set_bottom_border(p)

    add_heading("Summary")
    d.add_paragraph(data["summary"])

    if data.get("education"):
        add_heading("Education")
        for edu in data["education"]:
            header = " | ".join(
                part for part in (edu.get("institution"), edu.get("location")) if part
            )
            _add_entry_header(d, header, edu.get("dates", ""))
            degree_p = d.add_paragraph(edu.get("degree", ""))
            degree_p.paragraph_format.space_after = Pt(6)

    if data.get("experience"):
        add_heading("Experience")
        for job in data["experience"]:
            header = " | ".join(
                part for part in (job.get("company"), job.get("location")) if part
            )
            _add_entry_header(d, header, job.get("dates", ""))
            d.add_paragraph(job.get("title", ""), style=styles["entry_title"])
            bullets = job.get("bullets", [])
            for i, bullet in enumerate(bullets):
                p = d.add_paragraph(bullet, style="List Bullet")
                if i == len(bullets) - 1:
                    p.paragraph_format.space_after = Pt(8)

    if data.get("skills"):
        add_heading("Skills")
        d.add_paragraph(", ".join(data["skills"]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(out_path))


def convert_to_pdf(docx_path: Path, pdf_path: Path) -> None:
    from docx2pdf import convert

    convert(str(docx_path), str(pdf_path))


def archive_existing_outputs() -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    CREATE_DIR.mkdir(parents=True, exist_ok=True)

    archive_time = datetime.now().strftime("%H-%M-%S")
    for docx_file in CREATE_DIR.glob("out_resume_*.docx"):
        archived_name = f"{docx_file.stem}-{archive_time}{docx_file.suffix}"
        shutil.move(str(docx_file), str(ARCHIVE_DIR / archived_name))
        print(f"Archived {docx_file.name} -> resume_archive/{archived_name}")

    for pdf_file in CREATE_DIR.glob("out_resume_*.pdf"):
        pdf_file.unlink()
        print(f"Removed superseded {pdf_file.name} (only .docx versions are archived)")


def main() -> None:
    load_dotenv(ROOT / ".env")

    profile_path = find_latest("in_profile")
    resume_path = find_latest("in_resume")
    job_path = find_latest("in_job")

    print(f"Profile: {profile_path.name}")
    print(f"Prior resume: {resume_path.name}")
    print(f"Job posting: {job_path.name}")

    profile_text = read_docx_text(profile_path)
    resume_text = read_docx_text(resume_path)
    job_text = read_docx_text(job_path)

    print(f"Calling {MODEL} to tailor the resume...")
    data = call_llm(profile_text, resume_text, job_text)

    archive_existing_outputs()

    today = datetime.now().strftime("%Y-%m-%d")
    base_name = f"out_resume_{slugify_name(data['first_name'], data['last_name'])}_{today}"
    docx_path = CREATE_DIR / f"{base_name}.docx"
    pdf_path = CREATE_DIR / f"{base_name}.pdf"

    build_docx(data, docx_path)
    print(f"Wrote {docx_path.relative_to(ROOT)}")

    try:
        convert_to_pdf(docx_path, pdf_path)
        print(f"Wrote {pdf_path.relative_to(ROOT)}")
    except Exception as exc:  # docx2pdf requires MS Word via COM automation
        print(f"Warning: could not generate PDF ({exc}). The .docx was still created.")


if __name__ == "__main__":
    main()
