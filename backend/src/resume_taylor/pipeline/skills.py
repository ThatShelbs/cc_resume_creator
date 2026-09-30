"""Skills handling: pulling the skills list out of the draft, filtering entries that are
sentences rather than labels, and merging in the profile's tools/skills the posting also names."""

import re

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


def skill_key(skill: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", skill).strip().lower()


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
        if skill_key(s) and skill_key(s) in job_lower
    ]

    seen = {}
    for skill in tailored_skills + must_include:
        key = skill_key(skill)
        if key and key not in seen:
            seen[key] = skill
    return sorted(seen.values(), key=str.lower)
