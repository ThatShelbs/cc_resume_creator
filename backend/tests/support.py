"""Helpers shared by the test modules (put on the path by pyproject's pytest config)."""

from pathlib import Path

import docx
from fastapi.testclient import TestClient

from resume_taylor.app.main import create_app
from resume_taylor.layout import REPO_ROOT

TESTS_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = REPO_ROOT / "examples"
DENY_FIXTURE = TESTS_DIR / "deny_fixture.txt"
JOB_TEXT = (EXAMPLES_DIR / "in_job_example.txt").read_text(encoding="utf-8")


def write_docx(paragraphs, path):
    d = docx.Document()
    for text, style in paragraphs:
        d.add_paragraph(text, style=style)
    d.save(str(path))


def make_client(paths):
    """An API client for a data root, with the session token already set."""
    app = create_app(paths, "tok", extra_hosts={"testserver"})
    return TestClient(app, headers={"X-Taylor-Token": "tok"})
