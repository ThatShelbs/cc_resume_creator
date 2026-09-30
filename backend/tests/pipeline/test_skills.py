import pytest

from resume_taylor.pipeline.skills import (
    _split_skill_items,
    clean_skill_label,
    extract_skills_from_draft,
    merge_and_sort_skills,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Python", "Python"),
        ("Team Leadership (8+ years managing direct reports)", "Team Leadership"),
        ("8+ years of leadership", None),
        ("Scaled revenue of a $1B+ brand", None),
        ("Led the analytics function", None),
        ("Uplift Modeling (CausalML)", "Uplift Modeling (CausalML)"),
        ("one two three four five six seven eight", None),
    ],
)
def test_clean_skill_label(raw, expected):
    assert clean_skill_label(raw) == expected


def test_split_skill_items_keeps_parenthesized_commas():
    items = _split_skill_items("Python, Uplift Modeling (CausalML, PyLift) · SQL; Tableau | R")
    assert items == ["Python", "Uplift Modeling (CausalML, PyLift)", "SQL", "Tableau", "R"]


def test_extract_skills_categorized():
    draft = "## Core Competencies\n- **Tools:** Python | SQL\n- **Leadership:** Team Leadership, Vendor Management\n"
    assert extract_skills_from_draft(draft) == ["Python", "SQL", "Team Leadership", "Vendor Management"]


def test_extract_skills_flat_heading():
    draft = "## Summary\nText.\n\n## Skills\nPython, SQL, Forecasting\n\n## Experience\n- Did X\n"
    assert extract_skills_from_draft(draft) == ["Python", "SQL", "Forecasting"]


def test_merge_and_sort_skills_backfills_only_posting_terms():
    profile = {"tools": ["Python", "Tableau"], "skills": ["Forecasting"]}
    merged = merge_and_sort_skills(["sql", "Python (pandas)"], profile, "We need Python and Tableau.")
    assert merged == ["Python (pandas)", "sql", "Tableau"]
