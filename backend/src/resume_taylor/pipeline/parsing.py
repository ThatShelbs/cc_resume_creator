"""Deterministic extraction, with no LLM involved and none needed: contact info,
education, and each job's company/location/dates/title carry no tailoring judgment,
so parsing them straight out of the source .docx files is faster and more accurate
than asking a model to reproduce them."""

import re
import sys

from .sources import paras_and_name

PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")


def parse_applicant_info(profile) -> dict:
    """`profile` is a .docx path or a list of (style, text) paragraphs."""
    paras, profile_name = paras_and_name(profile)

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
    paras, resume_name = paras_and_name(resume, strip=False)

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


def parse_profile_skills(profile) -> dict:
    """Deterministically pull the flat skill/tool lists out of the profile's
    'Software/Tools' and 'Skills' sections (List Paragraph entries under those
    headers) — used as a truthful pool to backfill anything the model omits.
    Kept separate: tool names are unambiguous and safe to always list in full;
    the broader skills phrases benefit more from job-specific filtering."""
    paras, _ = paras_and_name(profile)

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
