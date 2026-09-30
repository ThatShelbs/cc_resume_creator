"""The project store, the evidence editors and live lint, and the background job runner."""

import json
import textwrap
import time

import pytest

from resume_taylor.app.services.jobs import JobManager
from resume_taylor.app.services.lint import lint_result
from resume_taylor.app.storage import facts as facts_mod
from resume_taylor.app.storage.projects import NotFound, ProjectError, ProjectStore, guess_company_role
from resume_taylor.pipeline.guards import load_deny_patterns
from resume_taylor.pipeline.sources import read_docx_text
from resume_taylor.sample_data import demo_data
from support import JOB_TEXT

# -- project store ---------------------------------------------------------------


def test_project_store_lifecycle(tmp_path):
    store = ProjectStore(tmp_path / "projects", tmp_path / "projects" / "_trash")
    with pytest.raises(ProjectError):
        store.create(job_text="too short")
    meta = store.create(job_text=JOB_TEXT, company="Example Co.", role="Director, Customer Analytics")
    assert meta.name == "Director, Customer Analytics at Example Co."
    assert store.get_job_text(meta.id).startswith("Director")
    assert [m.id for m in store.all()] == [meta.id]

    store.update(meta.id, {"status": "applied", "id": "hijack", "notes": " call recruiter "})
    got = store.get(meta.id)
    assert (got.status, got.id, got.notes) == ("applied", meta.id, "call recruiter")
    with pytest.raises(ProjectError):
        store.update(meta.id, {"status": "hired?"})

    # Generation installs outputs; the next one moves them into versions/.
    for n in (1, 2):
        staging = store.dir(meta.id) / f".staging-{n}"
        staging.mkdir()
        (staging / "out_resume_x.docx").write_text(f"v{n}")
        (staging / "out_resume_x.pdf").write_text(f"v{n}")
        (staging / "result.json").write_text(json.dumps({**demo_data.DEMO_RESULT, "summary": f"v{n}"}))
        store.promote(meta.id, staging, new_version=True)
        time.sleep(1.05)  # versions are keyed by second
    assert store.get_result(meta.id)["summary"] == "v2"
    versions = store.versions(meta.id)
    assert len(versions) == 1 and versions[0]["summary"] == "v1"
    assert [f["name"] for f in versions[0]["files"]] == ["out_resume_x.docx", "result.json"], "PDFs aren't archived"

    with pytest.raises(NotFound):
        store.safe_file(meta.id, "outputs", "..", "project.json")
    with pytest.raises(NotFound):
        store.dir("../../etc")

    copy = store.duplicate(meta.id)
    assert copy.id != meta.id and store.get_result(copy.id)["summary"] == "v2"

    trash_id = store.trash_project(meta.id)
    assert meta.id not in [m.id for m in store.all()]
    assert store.list_trash()[0]["id"] == trash_id
    restored = store.restore(trash_id)
    assert restored.id in [m.id for m in store.all()]


def test_guess_company_role():
    assert guess_company_role(JOB_TEXT) == {"company": "Example Co.", "role": "Director, Customer Analytics"}
    assert guess_company_role("Title: Staff Analyst\nCompany: Contoso\n" + "x" * 50) == {"company": "Contoso", "role": "Staff Analyst"}


# -- evidence: fact bank and never-claim list --------------------------------------


def test_fact_bank_ids_are_stable_and_header_kept(workspace):
    facts = facts_mod.read_facts(workspace.fact_bank_path)
    facts.append(facts_mod.Fact(text="A brand new fact.", employer="general"))
    facts.append(facts_mod.Fact(id="F001", text="Duplicate id gets a fresh one."))
    facts_mod.write_facts(workspace.fact_bank_path, facts)
    raw = workspace.fact_bank_path.read_text(encoding="utf-8")
    assert raw.startswith("# Demo fact bank"), "the comment header survives a save"
    again = facts_mod.read_facts(workspace.fact_bank_path)
    ids = [f.id for f in again]
    assert ids[:11] == [f"F{n:03d}" for n in range(1, 12)]
    assert ids[11:] == ["F012", "F013"] and len(set(ids)) == len(ids)
    issues = facts_mod.employer_issues(
        [facts_mod.Fact(id="F900", employer="Nowhere Inc", text="x")], ["Northwind Traders"]
    )
    assert issues == [{"id": "F900", "employer": "Nowhere Inc"}]


def test_deny_list_validation(tmp_path):
    text = "# comment\n\\bcertified\\b\n(unclosed\n"
    checked = facts_mod.check_deny_text(text)
    assert [c["error"] is None for c in checked] == [True, False]
    with pytest.raises(facts_mod.FactBankError, match="Line 3"):
        facts_mod.write_deny_text(tmp_path / "deny.txt", text)
    assert facts_mod.match_phrase("\\bcertified\\b", "An AWS Certified pro") == ["\\bcertified\\b"]


def test_lint_flags_each_problem_on_its_line(workspace):
    result = json.loads(json.dumps(demo_data.DEMO_RESULT))
    result["experience"][0]["bullets"][0]["text"] = "Certified wizard, 42% better."
    result["experience"][0]["bullets"][1]["ids"] = ["F999"]
    result["experience"][1]["bullets"][0]["text"] += " Also at Northwind Traders."
    source = read_docx_text(workspace.latest("in_profile")) + read_docx_text(workspace.latest("in_resume"))
    bank = {f.id: f.model_dump() for f in facts_mod.read_facts(workspace.fact_bank_path)}
    out = lint_result(result, source, bank, load_deny_patterns(workspace.deny_path))
    kinds = lambda key: {i["kind"] for i in out["bullets"].get(key, [])}  # noqa: E731
    assert {"deny", "number"} <= kinds("0.0")
    assert "citation" in kinds("0.1")
    assert "cross_employer" in kinds("1.0")
    assert out["counts"]["error"] >= 2


# -- background jobs ---------------------------------------------------------------


def _wait(job, timeout=30):
    end = time.time() + timeout
    while not job.done and time.time() < end:
        time.sleep(0.05)
    assert job.done, "job did not finish"


def test_job_runner_parses_markers_and_hints(tmp_path):
    script = tmp_path / "fake.py"
    script.write_text(textwrap.dedent("""\
        import sys
        print("::stage drafting", flush=True)
        print("working...", flush=True)
        print('::deny {"where": "summary", "pattern": "x", "text": "y"}', flush=True)
        sys.exit("Could not find the `claude` CLI on PATH.")
        """))
    jobs = JobManager()
    finished = []
    job = jobs.submit("generate", "Test", [str(script)], on_finish=lambda j: finished.append(j.outcome))
    _wait(job)
    assert job.status == "failed" and finished == ["failed"]
    assert "drafting" in job.stages_seen and job.deny[0]["where"] == "summary"
    assert "working..." in job.lines and not any(line.startswith("::") for line in job.lines)
    assert "npm install -g @anthropic-ai/claude-code" in job.hint


def test_job_success_waits_for_on_success(tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("print('::stage done')\n")
    jobs = JobManager()
    seen = []

    def on_success(j):
        seen.append(j.status)  # still "running" while results are installed
        time.sleep(0.2)

    job = jobs.submit("render", "Test", [str(script)], on_success=on_success)
    _wait(job)
    assert seen == ["running"] and job.status == "succeeded" and job.stage == "done"
