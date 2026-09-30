"""The cover letter validation, keyword coverage, and the tailoring report."""

from resume_taylor.config import COVER_LETTER_SKILL_PATH
from resume_taylor.pipeline.cover_letter import validate_cover_letter
from resume_taylor.pipeline.coverage import keyword_coverage
from resume_taylor.pipeline.prompts import load_skill
from resume_taylor.pipeline.report import write_report
from resume_taylor.pipeline.runtime import WARNINGS


def test_validate_cover_letter(bank):
    paragraphs = [
        "I saved $300k per year — with MMM. [F001]",
        "I did something unverifiable. [F999]",
        "I led a POC. [F003]",
        "Uncited middle.",
        "Uncited close.",
    ]
    result = validate_cover_letter(paragraphs, bank, "Saved $300k per year with MMM.")
    assert result == [
        ("I saved $300k per year, with MMM.", ["F001"]),
        ("Uncited middle.", []),
        ("Uncited close.", []),
    ]
    assert sum("dropped" in w for w in WARNINGS) == 2
    uncited = [w for w in WARNINGS if "uncited cover letter" in w]
    assert len(uncited) == 1 and "paragraph 4" in uncited[0]


def test_cover_letter_skill_loads_without_frontmatter():
    body = load_skill(COVER_LETTER_SKILL_PATH)
    assert not body.startswith("---")
    assert "<COVER_LETTER>" in body


def test_keyword_coverage():
    profile = {"tools": ["Python", "R", "Tableau"], "skills": ["Forecasting"]}
    facts = {"F001": {"tags": ["causal inference"]}}
    job = "Must know Python, R, and causal inference. Forecasting a plus."
    covered, missing = keyword_coverage(job, "Python expert in forecasting.", profile, facts)
    assert covered == ["Forecasting", "Python"]
    assert missing == ["causal inference"]  # "R" is under 2 chars and skipped


def test_write_report(tmp_path, bank):
    path = tmp_path / "r.md"
    write_report(
        path,
        {"Job posting": "in_job.docx"},
        "sonnet",
        "medium",
        ["something odd"],
        (["Python"], ["SQL"]),
        {"Acme": ["Saved $300k per year."]},
        {("Acme", "Saved $300k per year."): ["F001"]},
        bank,
        "raw draft",
    )
    report = path.read_text(encoding="utf-8")
    assert "something odd" in report
    assert "`F001` Saved $300k per year with MMM." in report
    assert "Missing: SQL" in report
