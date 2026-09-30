"""The profile editor's writer and the uploaded-resume ingestion."""

import textwrap

import make_examples
import pytest

from resume_taylor.app.storage import profile_store, resume_ingest
from resume_taylor.pipeline.parsing import parse_applicant_info, parse_prior_resume, parse_profile_skills
from resume_taylor.pipeline.sources import docx_paras


def test_profile_round_trip(workspace, tmp_path):
    profile = profile_store.read_profile(workspace.input_dir / "in_profile.docx")
    assert profile.contact.name == "Jordan Rivera"
    assert profile.contact.linkedin.startswith("linkedin.com")
    assert [s.title for s in profile.sections][:2] == ["Leadership", "Projects"]

    profile.sections.append(profile_store.Section(title="Certifications", items=["  Spaced\ttext\nline  "]))
    out = tmp_path / "saved.docx"
    backup_dir = tmp_path / "archive"
    out.write_bytes(b"old")  # something to back up
    profile_store.save_profile(profile, out, backup_dir)

    assert list(backup_dir.iterdir()), "the previous file is backed up before overwriting"
    contact = parse_applicant_info(out)
    assert (contact["first_name"], contact["last_name"], contact["email"]) == ("Jordan", "Rivera", "jordan.rivera@example.com")
    skills = parse_profile_skills(out)
    assert "Python" in skills["tools"] and "Forecasting" in skills["skills"]
    again = profile_store.read_profile(out)
    assert again.sections[-1].items == ["Spaced text line"], "items are single clean paragraphs"


def test_profile_validation_rejects_missing_email():
    bad = profile_store.Profile(contact=profile_store.Contact(name="Jordan Rivera"))
    with pytest.raises(profile_store.ProfileError):
        profile_store.validate_profile(bad)


PDF_LIKE = textwrap.dedent("""\
    JORDAN RIVERA
    jordan.rivera@example.com | (555) 010-0199 | Denver, CO
    PROFESSIONAL SUMMARY
    Analytics leader with 11 years of experience.
    EXPERIENCE
    Northwind Traders | Denver, CO Jan 2019 - Present
    Director, Analytics
    • Built a customer churn model that cut churn 12% in one
    year across every region.
    • Lead a team of 7 analysts.
    Senior Data Analyst 2016 - 2019
    Contoso Retail | Denver, CO
    • Automated weekly sales reporting, saving 10 hours per week.
    EDUCATION
    State University, Boulder, CO 2014
    B.S. Statistics
    SKILLS
    Python, SQL, Tableau
    """)


def test_heuristic_parser_handles_pdf_text():
    s = resume_ingest.verify(resume_ingest.heuristic_parse(PDF_LIKE), PDF_LIKE)
    assert [j.company for j in s.jobs] == ["Northwind Traders", "Contoso Retail"]
    nw, contoso = s.jobs
    assert (nw.title, nw.dates, nw.location) == ("Director, Analytics", "Jan 2019 - Present", "Denver, CO")
    assert nw.bullets[0] == "Built a customer churn model that cut churn 12% in one year across every region."
    assert contoso.title == "Senior Data Analyst", "title-first entries are swapped back"
    assert s.education[0].institution == "State University" and s.education[0].degree == "B.S. Statistics"
    assert s.summary.startswith("Analytics leader")
    assert not s.flags
    prefill = resume_ingest.prefill_contact(s)
    assert (prefill["name"], prefill["email"]) == ("Jordan Rivera", "jordan.rivera@example.com")
    assert prefill["skills"] == ["Python", "SQL", "Tableau"]


def test_verify_flags_text_not_in_source():
    s = resume_ingest.heuristic_parse(PDF_LIKE)
    s.jobs[0].bullets.append("Invented a time machine.")
    s.jobs[0].title = "Chief Everything Officer"
    flagged = {f.path for f in resume_ingest.verify(s, PDF_LIKE).flags}
    assert {"jobs.0.title", "jobs.0.bullets.2"} <= flagged


def test_structure_round_trips_through_pipeline_parser(tmp_path):
    s = resume_ingest.heuristic_parse(PDF_LIKE)
    s.jobs[0].company = "Northwind | Traders"  # a pipe would break the header line
    s.other_sections.append(resume_ingest.OtherSection(title="Certifications", lines=["Not | an employer"]))
    path = tmp_path / "in_resume_x.docx"
    resume_ingest.write_resume_docx(s, path)
    parsed = parse_prior_resume(path)
    assert [j["company"] for j in parsed["jobs"]] == ["Northwind / Traders", "Contoso Retail"]
    assert parsed["jobs"][0]["source_bullets"] == s.jobs[0].bullets
    back = resume_ingest.structure_from_paras(docx_paras(path, strip=False))
    assert back.summary == s.summary
    assert {o.title for o in back.other_sections} == {"Skills", "Certifications"}


def test_validate_structure_rejects_ambiguous_employers():
    s = resume_ingest.heuristic_parse(PDF_LIKE)
    s.jobs[1].company = s.jobs[0].company
    with pytest.raises(resume_ingest.IngestError, match="share the same company"):
        resume_ingest.validate_structure(s)


def test_ingest_structured_docx_parses_directly(tmp_path):
    make_examples.main(tmp_path)
    s = resume_ingest.ingest(tmp_path / "in_resume_example.docx")
    assert s.source == "docx"
    assert [j.company for j in s.jobs] == ["Northwind Traders", "Contoso Retail"]
