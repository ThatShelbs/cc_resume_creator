"""Fact bank loading and the bullet citations that tie output back to it."""

from resume_taylor.pipeline.factbank import (
    extract_citations,
    load_fact_bank,
    snap_employer,
    split_citation,
    validate_citations,
)
from resume_taylor.pipeline.runtime import WARNINGS


def test_split_citation():
    assert split_citation("Did X [F001, f004]") == ("Did X.", ["F001", "F004"])
    assert split_citation("Did X.") == ("Did X.", [])


def test_validate_citations_drops_bad_provenance(bank):
    bullets = {
        "Acme": [
            "Saved $300k per year. [F001]",
            "Unknown fact. [F999]",
            "Transplanted. [F002]",
            "Unassigned. [F003]",
            "Uncited bullet.",
            "General skill. [F004]",
        ]
    }
    cleaned, cites = validate_citations(bullets, bank)
    assert cleaned["Acme"] == ["Saved $300k per year.", "Uncited bullet.", "General skill."]
    assert cites["Acme"] == [["F001"], [], ["F004"]]
    assert sum("dropped" in w for w in WARNINGS) == 3
    assert any("uncited" in w for w in WARNINGS)


def test_validate_citations_warns_on_number_not_in_cited_fact(bank):
    validate_citations({"Acme": ["Saved $450k. [F001]"]}, bank)
    assert any("450" in w for w in WARNINGS)


def test_snap_employer():
    companies = ["Acme  Corp", "Globex"]
    assert snap_employer("acme corp", companies) == "Acme  Corp"
    assert snap_employer("General", companies) == "general"
    assert snap_employer("Initech", companies) is None


def test_load_fact_bank_flags_unknown_employer(tmp_path):
    path = tmp_path / "fact_bank.yaml"
    path.write_text(
        "facts:\n"
        "  - {id: F001, employer: acme, text: Did X}\n"
        "  - {id: F002, employer: Acmee, text: Did Y}\n",
        encoding="utf-8",
    )
    loaded = load_fact_bank(["Acme"], path)
    assert loaded["F001"]["employer"] == "Acme"
    assert loaded["F002"]["employer"] == "unassigned"
    assert any("Acmee" in w and "F002" in w for w in WARNINGS)


def test_extract_citations_inline():
    text, ids = extract_citations("I cut churn 12% [F001] and led 4 analysts [F002, f001].")
    assert text == "I cut churn 12% and led 4 analysts."
    assert ids == ["F001", "F002"]
