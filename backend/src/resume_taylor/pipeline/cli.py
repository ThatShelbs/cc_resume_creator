"""
Generate a tailored resume from the files in resume_input/.

Contact info, education, and each employer's company/location/dates/title are
extracted deterministically from resume_input/in_profile* and in_resume*;
there's no tailoring judgment involved in those fields, so the Claude Code CLI
(using your logged-in subscription, not a billed API key) is only asked to
produce the parts that actually require judgment: a tailored summary,
per-employer bullets selected from true source material, and a tailored skills
list (one drafting call, then a narrow JSON-transcription call). The result is
written to resume_create/ as .docx + .pdf + a _report.md audit trail; any
resume already there is moved to resume_archive/ (.docx and report only) first.

Requires the Claude Code CLI to be installed and logged in (`claude /login`).

Usage:
    python generate_resume.py [--job PATH] [--model M] [--effort E] [--no-pdf] [--dry-run]
    python -m resume_taylor.pipeline ...     (same thing)
"""

import argparse
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from ..config import ARCHIVE_DIR, CREATE_DIR, DO_NOT_CLAIM_EXAMPLE, DO_NOT_CLAIM_PATH, EFFORT, FACT_BANK_PATH, MODEL
from ..layout import REPO_ROOT
from .factbank import load_fact_bank
from .generate import generate
from .guards import load_deny_patterns
from .outputs import display_path, slugify_name, write_outputs
from .parsing import parse_applicant_info, parse_prior_resume, parse_profile_skills
from .render.templates import DEFAULT_TEMPLATE, TEMPLATES
from .report import write_report
from .result import load_result, result_bullets_by_company, result_citations, revalidate_result, save_result
from .runtime import WARNINGS, stage
from .sources import JOB_POSTING_EXTS, find_latest, read_docx_text, read_input_text


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a resume tailored to one job posting.")
    parser.add_argument(
        "--job",
        type=Path,
        help="job posting .docx/.pdf/.txt/.md (default: newest resume_input/in_job*)",
    )
    parser.add_argument("--profile", type=Path, help="profile .docx (default: newest resume_input/in_profile*)")
    parser.add_argument("--resume", type=Path, help="prior resume .docx (default: newest resume_input/in_resume*)")
    parser.add_argument(
        "--fact-bank", type=Path, help=f"fact bank YAML (default: {FACT_BANK_PATH.relative_to(REPO_ROOT)})"
    )
    parser.add_argument("--deny", type=Path, help=f"never-claim list (default: {DO_NOT_CLAIM_PATH.name}, else the starter {DO_NOT_CLAIM_EXAMPLE.name})")
    parser.add_argument(
        "--cover-letter",
        action="store_true",
        help="also write a cover letter built from the validated resume content",
    )
    parser.add_argument(
        "--archive-job",
        action="store_true",
        help="after a successful run, move the job posting into resume_archive/",
    )
    parser.add_argument("--model", default=MODEL, help=f"Claude model (default: {MODEL})")
    parser.add_argument("--effort", default=EFFORT, help=f"reasoning effort (default: {EFFORT})")
    parser.add_argument(
        "--template",
        choices=sorted(TEMPLATES),
        default=DEFAULT_TEMPLATE,
        help=f"resume layout (default: {DEFAULT_TEMPLATE})",
    )
    parser.add_argument("--out-dir", type=Path, help="where to write outputs (default: resume_create/)")
    parser.add_argument("--archive-dir", type=Path, help="where superseded outputs go (default: resume_archive/)")
    parser.add_argument("--result-json", type=Path, help="also save the structured, editable result here")
    parser.add_argument(
        "--render-json",
        type=Path,
        help="skip generation: re-validate and render a saved result JSON (no Claude call)",
    )
    parser.add_argument("--no-pdf", action="store_true", help="skip the Word-based PDF export")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run generation and validation, print the result and a report, but archive/write nothing",
    )
    return parser.parse_args(argv)


def _require(path: Path, what: str) -> Path:
    if not path.exists():
        sys.exit(f"{what} not found: {path}")
    return path


def load_context(args: argparse.Namespace) -> dict:
    """Locate and parse every input. Shared by generation and --render-json."""
    profile_path = _require(args.profile or find_latest("in_profile"), "Profile")
    resume_path = _require(args.resume or find_latest("in_resume"), "Prior resume")
    job_path = _require(args.job or find_latest("in_job", JOB_POSTING_EXTS), "Job posting")
    deny_path = args.deny or DO_NOT_CLAIM_PATH

    print(f"Profile: {profile_path.name}")
    print(f"Prior resume: {resume_path.name}")
    print(f"Job posting: {job_path.name}")

    contact = parse_applicant_info(profile_path)
    parsed_resume = parse_prior_resume(resume_path)
    companies = [job["company"] for job in parsed_resume["jobs"]]
    profile_text = read_docx_text(profile_path)
    resume_text = read_docx_text(resume_path)
    job_text = read_input_text(job_path)
    if not job_text:
        sys.exit(f"No text could be read from {job_path.name} (a scanned PDF?). Save it as .txt instead.")

    return {
        "profile_path": profile_path,
        "resume_path": resume_path,
        "job_path": job_path,
        "contact": contact,
        "parsed_resume": parsed_resume,
        "companies": companies,
        "profile_text": profile_text,
        "resume_text": resume_text,
        "job_text": job_text,
        "source_text": profile_text + "\n" + resume_text,
        "deny_patterns": load_deny_patterns(deny_path),
        "deny_name": deny_path.name,
        "fact_bank_path": args.fact_bank or FACT_BANK_PATH,
        "profile_skills": parse_profile_skills(profile_path),
        "inputs": {
            "Profile": profile_path.name,
            "Prior resume": resume_path.name,
            "Job posting": job_path.name,
        },
    }


def main(argv=None) -> None:
    args = parse_args(argv)
    WARNINGS.clear()
    stage("preparing")

    ctx = load_context(args)
    ctx["fact_bank"] = load_fact_bank(ctx["companies"], ctx["fact_bank_path"])
    if args.render_json:
        print(f"Re-rendering {args.render_json.name} (no Claude call)...")
    elif ctx["fact_bank"]:
        print(f"Fact bank: {len(ctx['fact_bank'])} facts (citations enforced)")
    else:
        print(
            f"Fact bank: none at {display_path(ctx['fact_bank_path'])}; bullets won't be "
            "provenance-checked. Run `python build_fact_bank.py` to create one."
        )

    if args.render_json:
        result = load_result(args.render_json)
        stage("validating")
        revalidate_result(result, ctx)
    else:
        result = generate(args, ctx)
        result["generation_warnings"] = list(WARNINGS)

    out_dir = args.out_dir or CREATE_DIR
    if args.dry_run:
        print(f"\n--- DRY RUN: nothing archived or written to {out_dir.name}/ ---\n")
        print(f"SUMMARY\n{result['summary']}\n")
        for job in result["experience"]:
            print(job["company"])
            for bullet in job["bullets"]:
                print(f"  - {bullet['text']}")
        print(f"\nSKILLS\n{', '.join(result['skills'])}\n")
        if result.get("cover_letter"):
            print("COVER LETTER\n" + "\n\n".join(p["text"] for p in result["cover_letter"]) + "\n")
        base = f"out_resume_{slugify_name(result['contact']['first_name'], result['contact']['last_name'])}"
        report_path = Path(tempfile.gettempdir()) / f"{base}_{datetime.now():%Y-%m-%d}_report.md"
        coverage = result.get("coverage") or {}
        write_report(
            report_path,
            result["inputs"],
            result.get("model", args.model),
            result.get("effort", args.effort),
            WARNINGS,
            (coverage.get("covered", []), coverage.get("missing", [])),
            result_bullets_by_company(result),
            result_citations(result),
            ctx["fact_bank"],
            result.get("draft", ""),
            cover_letter=[(p["text"], p["ids"]) for p in result.get("cover_letter") or []] or None,
        )
    else:
        report_path = write_outputs(
            result, out_dir, args.archive_dir, args.template, args.no_pdf, ctx["fact_bank"]
        )
        if args.archive_job and not args.render_json:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(str(ctx["job_path"]), str(ARCHIVE_DIR / ctx["job_path"].name))
            print(f"Archived job posting {ctx['job_path'].name} -> resume_archive/")

    result["warnings"] = list(WARNINGS)
    if args.result_json:
        save_result(result, args.result_json)
        print(f"Saved result to {display_path(args.result_json)}")
    stage("done")
    print(f"{len(WARNINGS)} warning(s); see {report_path}")
