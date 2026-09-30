"""Prompt assets: the skill loader (the skills hold the judgment and writing rules, one
source of truth shared with interactive use) and the pipeline-specific I/O contracts."""

import re
import sys
from pathlib import Path

from ..config import TAILORING_SKILL_PATH

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
