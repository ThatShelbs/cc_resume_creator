"""Reading the input files and parsing the profile / prior resume."""

import os

import docx
import make_examples
import pytest

from resume_taylor.pipeline.factbank import load_fact_bank
from resume_taylor.pipeline.parsing import parse_applicant_info, parse_prior_resume, parse_profile_skills
from resume_taylor.pipeline.runtime import WARNINGS
from resume_taylor.pipeline.sources import JOB_POSTING_EXTS, find_latest, read_input_text


def test_find_latest_uses_mtime(tmp_path):
    older, newer = tmp_path / "in_job_zeta.docx", tmp_path / "in_job_alpha.docx"
    older.write_bytes(b"")
    newer.write_bytes(b"")
    os.utime(older, (1_000_000, 1_000_000))
    os.utime(newer, (2_000_000, 2_000_000))
    assert find_latest("in_job", directory=tmp_path) == newer


def test_find_latest_job_accepts_text_formats(tmp_path):
    job = tmp_path / "in_job_example.txt"
    job.write_text("Director, Analytics\nPython required.", encoding="utf-8")
    (tmp_path / "in_job_notes.json").write_text("{}", encoding="utf-8")
    found = find_latest("in_job", JOB_POSTING_EXTS, directory=tmp_path)
    assert found == job
    assert "Python required." in read_input_text(found)
    with pytest.raises(SystemExit):
        find_latest("in_profile", directory=tmp_path)


def test_parse_prior_resume_roundtrip(tmp_path):
    d = docx.Document()
    for text, style in [
        ("EDUCATION", "Normal"),
        ("State University | Springfield\t2008 - 2012", "Normal"),
        ("B.S. Statistics", "Normal"),
        ("EXPERIENCE", "Normal"),
        ("Acme | Chicago, IL\t2015 - Present", "Normal"),
        ("Lead Data Scientist", "Normal"),
        ("Built a churn model.", "List Paragraph"),
        ("Saved $300k.", "List Paragraph"),
    ]:
        d.add_paragraph(text, style=style)
    path = tmp_path / "in_resume.docx"
    d.save(str(path))

    parsed = parse_prior_resume(path)
    assert parsed["education"][0]["institution"] == "State University"
    job = parsed["jobs"][0]
    assert (job["company"], job["location"], job["dates"], job["title"]) == (
        "Acme",
        "Chicago, IL",
        "2015 - Present",
        "Lead Data Scientist",
    )
    assert job["source_bullets"] == ["Built a churn model.", "Saved $300k."]


def test_examples_parse(tmp_path):
    make_examples.main(tmp_path)
    contact = parse_applicant_info(tmp_path / "in_profile_example.docx")
    assert (contact["first_name"], contact["email"]) == ("Jordan", "jordan.rivera@example.com")
    jobs = parse_prior_resume(tmp_path / "in_resume_example.docx")["jobs"]
    companies = [j["company"] for j in jobs]
    assert companies == ["Northwind Traders", "Contoso Retail"]
    skills = parse_profile_skills(tmp_path / "in_profile_example.docx")
    assert skills == {"tools": ["Python", "SQL", "Tableau"], "skills": ["Forecasting", "Team Leadership", "Stakeholder Management"]}
    bank = load_fact_bank(companies, tmp_path / "fact_bank.example.yaml")
    assert len(bank) == 5 and not WARNINGS
