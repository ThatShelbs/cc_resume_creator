"""The profile as an editable model, round-tripped through the exact .docx
layout the pipeline parses: an "Applicant info" heading followed by contact
lines, then Normal-style section headings, each followed by List Paragraph
items. Whatever the editor saves, parse_applicant_info() and
parse_profile_skills() read back unchanged."""

import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import docx
from pydantic import BaseModel, Field

from resume_taylor.pipeline.parsing import PHONE_RE, parse_applicant_info
from resume_taylor.pipeline.sources import docx_paras

CONTACT_HEADINGS = ("applicant info", "contact", "contact info")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")


class Contact(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""


class Section(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str
    items: list[str] = []


class Profile(BaseModel):
    contact: Contact = Contact()
    sections: list[Section] = []


class ProfileError(ValueError):
    pass


def _clean(text: str) -> str:
    # One paragraph per item: a stray newline or tab would split it or be
    # misread as the header's right-aligned dates.
    return re.sub(r"\s+", " ", text or "").strip()


def profile_from_paras(paras: list) -> Profile:
    contact_lines: list = []
    sections: list = []
    current = None
    in_contact = False
    for style, text in paras:
        key = text.strip().rstrip(":").strip().lower()
        if style == "Normal":
            in_contact = key in CONTACT_HEADINGS
            current = None
            if not in_contact:
                current = Section(title=text.strip().rstrip(":").strip())
                sections.append(current)
            continue
        if in_contact:
            contact_lines.append(text.strip())
        elif current is not None:
            current.items.append(text.strip())
        else:
            # Items before any heading: keep them rather than silently drop.
            current = Section(title="Other")
            sections.append(current)
            current.items.append(text.strip())

    email = next((l for l in contact_lines if "@" in l), "")
    phone = next((l for l in contact_lines if PHONE_RE.search(l)), "")
    linkedin = next((l for l in contact_lines if "linkedin.com" in l.lower()), "")
    remaining = [l for l in contact_lines if l not in (email, phone, linkedin)]
    contact = Contact(
        name=remaining[0] if remaining else "",
        email=email,
        phone=phone,
        location=", ".join(remaining[1:]),
        linkedin=linkedin,
    )
    return Profile(contact=contact, sections=sections)


def read_profile(path: Path) -> Profile:
    return profile_from_paras(docx_paras(path))


def profile_to_paras(profile: Profile) -> list:
    c = profile.contact
    paras = [("Normal", "Applicant info")]
    for value in (c.name, c.email, c.phone, c.location, c.linkedin):
        value = _clean(value)
        if value:
            paras.append(("List Paragraph", value))
    for section in profile.sections:
        title = _clean(section.title)
        items = [_clean(i) for i in section.items if _clean(i)]
        if not title:
            continue
        if title.lower() in CONTACT_HEADINGS:
            title = f"{title} (details)"
        paras.append(("Normal", title))
        paras.extend(("List Paragraph", item) for item in items)
    return paras


def validate_profile(profile: Profile) -> None:
    c = profile.contact
    if not _clean(c.name) or len(_clean(c.name).split()) < 1:
        raise ProfileError("Your name is required.")
    if not EMAIL_RE.search(c.email or ""):
        raise ProfileError("A valid email address is required.")
    # Prove the pipeline will read it back, before anything is written.
    try:
        parse_applicant_info(profile_to_paras(profile))
    except SystemExit as exc:
        raise ProfileError(str(exc)) from None


def write_profile_docx(profile: Profile, path: Path) -> None:
    d = docx.Document()
    for style, text in profile_to_paras(profile):
        d.add_paragraph(text, style=style)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.docx")
    d.save(str(tmp))
    tmp.replace(path)


def backup(path: Path, archive_dir: Path) -> Path | None:
    if not path.exists():
        return None
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    dest = archive_dir / f"{path.stem}-{stamp}{path.suffix}"
    shutil.copy2(path, dest)
    return dest


def save_profile(profile: Profile, path: Path, archive_dir: Path) -> Path | None:
    """Validate, back up the current file, then write. Returns the backup path."""
    validate_profile(profile)
    saved = backup(path, archive_dir)
    write_profile_docx(profile, path)
    return saved
