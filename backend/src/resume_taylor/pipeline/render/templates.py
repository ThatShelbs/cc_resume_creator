"""Resume template definitions. Every template stays inside the ATS-safe envelope."""

from dataclasses import dataclass

from docx.shared import RGBColor

INK = RGBColor(0x1F, 0x2A, 0x44)


MUTED = RGBColor(0x44, 0x44, 0x44)


RULE_COLOR = "1F2A44"


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
