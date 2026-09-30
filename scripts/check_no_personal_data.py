"""Fail if personal files are (or are about to be) committed.

    python scripts/check_no_personal_data.py            # everything tracked
    python scripts/check_no_personal_data.py --staged   # only what is staged
    python scripts/check_no_personal_data.py --history  # every file in all history

Resumes, job postings, the fact bank, API keys and per-job project folders
must never reach GitHub. Sample files that ship on purpose live in examples/
and docs/ (and tests/) and are allowed.

Install as a git pre-commit hook with:  python scripts/check_no_personal_data.py --install-hook
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN = [
    (re.compile(r"(^|/)\.env$"), "a .env file (holds your API key)"),
    (re.compile(r"(^|/)secrets\.json$"), "secrets.json (holds your API key)"),
    (re.compile(r"(^|/)app_settings\.json$"), "app_settings.json"),
    (re.compile(r"^projects/"), "a job-application project folder"),
    (re.compile(r"^demo_workspace/"), "a generated demo workspace"),
    (re.compile(r"^(resume_input|resume_create|resume_archive)/(?!\.gitkeep$)"), "personal resume data"),
    (re.compile(r"^do_not_claim\.txt$"), "your personal never-claim list (only the .example is tracked)"),
    (re.compile(r"(^|/)fact_bank\.ya?ml$"), "a personal fact bank (only examples/fact_bank.example.yaml is allowed)"),
    (re.compile(r"(^|/)(in|out)_(resume|profile|job|cover_letter)[^/]*$"), "an input or generated resume file"),
]
ALLOWED_DOC_DIRS = ("examples/", "docs/", "backend/tests/")
DOC_EXTS = (".docx", ".pdf", ".doc")
SECRET_PATTERN = re.compile(rb"sk-ant-[A-Za-z0-9_\-]{20,}")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def problem(path: str) -> str | None:
    norm = path.replace("\\", "/")
    if norm.startswith(ALLOWED_DOC_DIRS) or norm.startswith("frontend/dist/"):
        return None
    for pattern, why in FORBIDDEN:
        if pattern.search(norm) and norm != ".env.example":
            return why
    if norm.lower().endswith(DOC_EXTS):
        return "a Word/PDF document outside examples/ and docs/"
    return None


def staged_secret(path: str) -> bool:
    try:
        blob = subprocess.run(["git", "show", f":{path}"], cwd=ROOT, capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return False
    return bool(SECRET_PATTERN.search(blob))


def install_hook() -> None:
    hook = ROOT / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text('#!/bin/sh\npython scripts/check_no_personal_data.py --staged || exit 1\n', encoding="utf-8")
    print(f"Installed {hook}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--install-hook", action="store_true")
    args = parser.parse_args()
    if args.install_hook:
        install_hook()
        return 0

    if args.history:
        paths = sorted(set(git("log", "--all", "--name-only", "--pretty=format:").split("\n")) - {""})
    elif args.staged:
        paths = [p for p in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").split("\n") if p]
    else:
        paths = [p for p in git("ls-files").split("\n") if p]

    bad = [(p, why) for p in paths if (why := problem(p))]
    secrets = [p for p in paths if args.staged and staged_secret(p)]
    for p, why in bad:
        print(f"BLOCKED: {p}\n         looks like {why}")
    for p in secrets:
        print(f"BLOCKED: {p}\n         contains what looks like an Anthropic API key")
    if bad or secrets:
        print("\nThese files hold personal data or secrets and must not be committed.")
        return 1
    print(f"OK: {len(paths)} file(s) checked, nothing personal found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
