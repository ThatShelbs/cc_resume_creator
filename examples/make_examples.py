"""
Build the anonymized example inputs in this folder: a fake profile, prior
resume, and job posting laid out exactly the way generate_resume.py parses
them. Copy them into resume_input/ (renamed to in_profile*.docx,
in_resume*.docx, in_job*.txt) to try the pipeline without real data, or use
them as a template for your own files.

Usage:
    python examples/make_examples.py
"""

from pathlib import Path

import docx

HERE = Path(__file__).resolve().parent

# (text, style) pairs. Section headings are "Normal"; the lines under
# "Applicant info" and every bullet/skill are "List Paragraph". Experience
# and education headers are "Name | Location<TAB>Dates", followed by one
# Normal title/degree line.
PROFILE = [
    ("Applicant info", "Normal"),
    ("Jordan Rivera", "List Paragraph"),
    ("jordan.rivera@example.com", "List Paragraph"),
    ("(555) 010-0199", "List Paragraph"),
    ("Denver, CO", "List Paragraph"),
    ("Experience", "Normal"),
    ("Northwind Traders: built a customer churn model that cut churn 12% in one year.", "List Paragraph"),
    ("Northwind Traders: led a team of 4 analysts.", "List Paragraph"),
    ("Contoso Retail: automated weekly sales reporting, saving 10 hours per week.", "List Paragraph"),
    ("Software/Tools", "Normal"),
    ("Python", "List Paragraph"),
    ("SQL", "List Paragraph"),
    ("Tableau", "List Paragraph"),
    ("Skills", "Normal"),
    ("Forecasting", "List Paragraph"),
    ("Team Leadership", "List Paragraph"),
    ("Stakeholder Management", "List Paragraph"),
]

RESUME = [
    ("Summary", "Normal"),
    ("Analytics leader with 8 years of experience.", "Normal"),
    ("Education", "Normal"),
    ("State University | Boulder, CO\t2010 - 2014", "Normal"),
    ("B.S. Statistics", "Normal"),
    ("Experience", "Normal"),
    ("Northwind Traders | Denver, CO\t2019 - Present", "Normal"),
    ("Analytics Manager", "Normal"),
    ("Built a customer churn model that cut churn 12% in one year.", "List Paragraph"),
    ("Led a team of 4 analysts.", "List Paragraph"),
    ("Contoso Retail | Denver, CO\t2014 - 2019", "Normal"),
    ("Data Analyst", "Normal"),
    ("Automated weekly sales reporting, saving 10 hours per week.", "List Paragraph"),
]

JOB = """Director, Customer Analytics (Example Co.)

You will lead a team of analysts, own churn and retention modeling, and build
forecasting for the commercial org. You have Python, SQL, and Tableau
experience and strong stakeholder management skills.
"""

FACT_BANK = """\
# Example fact bank. See build_fact_bank.py for how a real one is drafted.
facts:
- id: F001
  employer: Northwind Traders
  kind: accomplishment
  text: Built a customer churn model that cut churn 12% in one year.
  metrics: ["12%"]
  tags: [churn modeling, retention]
- id: F002
  employer: Northwind Traders
  kind: responsibility
  text: Led a team of 4 analysts.
  metrics: ["4"]
  tags: [team leadership]
- id: F003
  employer: Contoso Retail
  kind: accomplishment
  text: Automated weekly sales reporting, saving 10 hours per week.
  metrics: ["10 hours"]
  tags: [automation, reporting]
- id: F004
  employer: general
  kind: tool
  text: Python, SQL, and Tableau.
  metrics: []
  tags: [python, sql, tableau]
- id: F005
  employer: general
  kind: skill
  text: Forecasting and stakeholder management.
  metrics: []
  tags: [forecasting, stakeholder management]
"""


def build_docx(paragraphs: list, path: Path) -> None:
    d = docx.Document()
    for text, style in paragraphs:
        d.add_paragraph(text, style=style)
    d.save(str(path))


def main(out_dir: Path = HERE) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    build_docx(PROFILE, out_dir / "in_profile_example.docx")
    build_docx(RESUME, out_dir / "in_resume_example.docx")
    (out_dir / "in_job_example.txt").write_text(JOB, encoding="utf-8")
    (out_dir / "fact_bank.example.yaml").write_text(FACT_BANK, encoding="utf-8")
    print(f"Wrote example inputs to {out_dir}")


if __name__ == "__main__":
    main()
