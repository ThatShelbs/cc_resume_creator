"""The pipeline as a command: end to end against a fake `claude`, and --render-json.

`run_cli` starts a real subprocess through the root `generate_resume.py` shim (the
same entry point people use), with a stand-in `claude` first on PATH.
"""

import json
import os
import subprocess
import sys

import pytest

from resume_taylor.claude_cli import clean_subprocess_env
from resume_taylor.layout import REPO_ROOT
from resume_taylor.sample_data import demo_data
from support import DENY_FIXTURE, EXAMPLES_DIR, write_docx

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def fake_claude_env(tmp_path):
    """An environment whose `claude` is tests/pipeline/fake_claude.py."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = os.path.join(HERE, "fake_claude.py")
    if sys.platform == "win32":
        (bin_dir / "claude.cmd").write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    else:
        shim = bin_dir / "claude"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("CLAUDE", "ANTHROPIC"))}
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("TAYLOR_PROGRESS", None)
    return env


@pytest.fixture
def inputs(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    write_docx(demo_data.PROFILE, src / "in_profile.docx")
    write_docx(demo_data.RESUME, src / "in_resume_Jordan-Rivera.docx")
    (src / "in_job.txt").write_text(demo_data.JOBS["lumen"]["text"], encoding="utf-8")
    (src / "fact_bank.yaml").write_text(demo_data.FACT_BANK, encoding="utf-8")
    return [
        "--profile", str(src / "in_profile.docx"),
        "--resume", str(src / "in_resume_Jordan-Rivera.docx"),
        "--job", str(src / "in_job.txt"),
        "--fact-bank", str(src / "fact_bank.yaml"),
        "--deny", str(DENY_FIXTURE),
    ]


def run_cli(args, env):
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "generate_resume.py"), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT), env=env,
    )


def test_generate_end_to_end_with_a_fake_claude(tmp_path, inputs, fake_claude_env):
    out, arch, result_json = tmp_path / "out", tmp_path / "arch", tmp_path / "result.json"
    args = [*inputs, "--out-dir", out, "--archive-dir", arch, "--result-json", result_json, "--no-pdf", "--cover-letter"]
    proc = run_cli(args, {**fake_claude_env, "TAYLOR_PROGRESS": "1"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for stage in ("preparing", "drafting", "structuring", "validating", "cover_letter", "rendering", "done"):
        assert f"::stage {stage}" in proc.stdout

    result = json.loads(result_json.read_text(encoding="utf-8"))
    assert "11+ years" in result["summary"] and "—" not in result["summary"], "inflated years and em dashes are corrected"
    bullets = {j["company"]: [b["text"] for b in j["bullets"]] for j in result["experience"]}
    assert len(bullets["Northwind Traders"]) == 6, "only the bullet citing another employer's fact is dropped"
    assert "Built store-level demand forecasts that reduced stockouts 18%." not in bullets["Northwind Traders"]
    assert len(bullets["Fabrikam Health"]) == 2, "the bullet naming another employer is dropped"
    assert result["skills"][0] == "A/B Testing" and "Rust" in result["skills"], "skills come from the draft, not the JSON"
    assert len(result["cover_letter"]) == 3
    warnings = "\n".join(result["warnings"])
    for expected in ("$95M", "cites F006", "uncited bullet", "mentioned Northwind Traders", "comparison phrasing", "'Rust'"):
        assert expected in warnings

    names = sorted(p.name for p in out.iterdir())
    assert [n.rsplit(".", 1)[-1] for n in names] == ["docx", "docx", "md"]
    report = next(out.glob("*_report.md")).read_text(encoding="utf-8")
    assert "## Bullets and provenance" in report and "## Cover letter" in report

    # A second run archives the first one's .docx and report.
    again = run_cli(args, fake_claude_env)
    assert again.returncode == 0, again.stdout + again.stderr
    assert len(list(arch.iterdir())) == 3


def test_generate_aborts_on_a_never_claim_hit(tmp_path, inputs, fake_claude_env):
    out = tmp_path / "out"
    proc = run_cli(
        [*inputs, "--out-dir", out, "--archive-dir", tmp_path / "arch", "--no-pdf"],
        {**fake_claude_env, "FAKE_CLAUDE_MODE": "prohibited", "TAYLOR_PROGRESS": "1"},
    )
    assert proc.returncode != 0
    assert "::deny " in proc.stdout and "Nothing was archived or overwritten" in proc.stderr
    assert not out.exists() or not any(out.iterdir())


def test_entry_points_all_answer_help():
    for script in ("generate_resume.py", "build_fact_bank.py", "launcher.py"):
        proc = subprocess.run([sys.executable, str(REPO_ROOT / script), "--help"], capture_output=True, text=True,
                              encoding="utf-8", cwd=str(REPO_ROOT))
        assert proc.returncode == 0 and "usage:" in proc.stdout, script
    proc = subprocess.run([sys.executable, "-m", "resume_taylor.pipeline", "--help"], capture_output=True, text=True,
                          encoding="utf-8", cwd=str(REPO_ROOT), env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "backend" / "src")})
    assert proc.returncode == 0 and "usage:" in proc.stdout


def render(workspace, result_path, out_dir, *extra):
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "generate_resume.py"),
         "--profile", str(workspace.latest("in_profile")),
         "--resume", str(workspace.latest("in_resume")),
         "--job", str(EXAMPLES_DIR / "in_job_example.txt"),
         "--fact-bank", str(workspace.fact_bank_path),
         "--deny", str(workspace.deny_path),
         "--render-json", str(result_path), "--result-json", str(result_path),
         "--out-dir", str(out_dir), "--no-pdf", *extra],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
        env={**os.environ, "TAYLOR_PROGRESS": "1", "PYTHONIOENCODING": "utf-8"},
    )


def test_render_json_revalidates_and_writes(workspace, tmp_path):
    result = json.loads(json.dumps(demo_data.DEMO_RESULT))
    result["summary"] += " Also tried 97 things — all of them."
    result["experience"][0]["bullets"].append({"text": "Uncited but true: led a team of 7 analysts.", "ids": []})
    rp = tmp_path / "result.json"
    rp.write_text(json.dumps(result), encoding="utf-8")
    out = tmp_path / "out"
    proc = render(workspace, rp, out, "--template", "modern")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "::stage rendering" in proc.stdout
    names = sorted(p.name for p in out.iterdir())
    assert any(n.endswith(".docx") for n in names) and any(n.endswith("_report.md") for n in names)
    saved = json.loads(rp.read_text(encoding="utf-8"))
    assert "—" not in saved["summary"], "em dashes are replaced on render"
    assert saved["template"] == "modern"
    assert any("97" in w for w in saved["warnings"])
    assert any("uncited bullet" in w for w in saved["warnings"])
    assert saved["coverage"]["covered"], "coverage is recomputed against the posting"

    # A second render archives the first one's outputs.
    archive = tmp_path / "archive"
    assert render(workspace, rp, out, "--archive-dir", str(archive)).returncode == 0
    assert any(p.suffix == ".docx" for p in archive.iterdir())


def test_render_json_blocks_never_claim_hits(workspace, tmp_path):
    result = json.loads(json.dumps(demo_data.DEMO_RESULT))
    result["experience"][0]["bullets"][0]["text"] = "AWS certified solutions architect."
    rp = tmp_path / "result.json"
    rp.write_text(json.dumps(result), encoding="utf-8")
    out = tmp_path / "out"
    proc = render(workspace, rp, out)
    assert proc.returncode != 0
    assert "::deny " in proc.stdout
    assert not out.exists() or not any(out.iterdir()), "nothing is written when a claim is prohibited"


def test_generator_env_keeps_only_the_api_key(monkeypatch):
    key = "sk-ant-api03-" + "A1b2C3d4E5" * 3
    monkeypatch.setenv("ANTHROPIC_API_KEY", key)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("CLAUDE_CODE_FOO", "1")
    env = clean_subprocess_env()
    assert env.get("ANTHROPIC_API_KEY") == key
    assert "ANTHROPIC_BASE_URL" not in env and "CLAUDE_CODE_FOO" not in env

