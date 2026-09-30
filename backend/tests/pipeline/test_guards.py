"""The deterministic validation/correction guards."""

from resume_taylor.pipeline.guards import (
    find_deny_violations,
    fix_years_of_experience,
    load_deny_patterns,
    remove_em_dashes,
    strip_cross_employer_mentions,
)
from resume_taylor.pipeline.runtime import WARNINGS
from support import DENY_FIXTURE


def test_deny_list_blocks_identities_not_collaboration():
    patterns = load_deny_patterns(DENY_FIXTURE)
    ok = find_deny_violations("Partnered with software engineers.", {}, [], patterns)
    bad = find_deny_violations("Worked as a full-stack engineer.", {}, ["Figma"], patterns)
    assert ok == []
    assert len(bad) == 2


def test_fix_years_of_experience():
    src = "Data scientist with 10 years of experience."
    assert fix_years_of_experience("Leader with 15+ years of experience.", src) == (
        "Leader with 10+ years of experience."
    )
    assert fix_years_of_experience("Leader with 11 years of experience.", src).startswith("Leader with 11")


def test_fix_years_catches_loose_phrasing():
    src = "Data scientist with 10 years of experience."
    assert fix_years_of_experience("Over 15 years leading teams.", src) == "Over 10 years leading teams."
    assert fix_years_of_experience("Built 3 years of models.", src) == "Built 3 years of models."


def test_remove_em_dashes():
    assert remove_em_dashes("Built X — and Y") == "Built X, and Y"
    assert remove_em_dashes("Built X – and Y") == "Built X, and Y"
    assert remove_em_dashes("From 2019–2021") == "From 2019–2021"


def test_strip_cross_employer_mentions():
    out = strip_cross_employer_mentions(
        {"Allstate Insurance": ["Did X at Acme.", "Did Y."], "Acme Corp": ["Did Z."]}
    )
    assert out == {"Allstate Insurance": ["Did Y."], "Acme Corp": ["Did Z."]}
    assert len(WARNINGS) == 1
