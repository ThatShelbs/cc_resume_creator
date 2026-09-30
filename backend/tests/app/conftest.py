"""Fixtures for the app tests: an API client whose pipeline is a fake script, so no
Claude call (or Word) is ever needed."""

import json
import textwrap

import pytest

from resume_taylor.app.storage.paths import Paths
from resume_taylor.sample_data import demo_data
from support import make_client

FAKE_PIPELINE = textwrap.dedent("""\
    # Stands in for the pipeline: writes a result and a .docx.
    import json, sys
    from pathlib import Path
    args = sys.argv[1:]
    get = lambda flag: args[args.index(flag) + 1] if flag in args else None
    out = Path(get("--out-dir")); out.mkdir(parents=True, exist_ok=True)
    for stage in ("preparing", "drafting", "structuring", "validating", "rendering"):
        print(f"::stage {stage}", flush=True)
    result = json.loads(Path(get("--render-json")).read_text()) if get("--render-json") else json.loads(RESULT)
    result["template"] = get("--template")
    Path(get("--result-json")).write_text(json.dumps(result))
    (out / "out_resume_jordan-rivera_2026-09-29.docx").write_text("docx")
    (out / "out_resume_jordan-rivera_2026-09-29_report.md").write_text("# Report")
    print("::stage done", flush=True)
    """)


@pytest.fixture
def client(workspace, tmp_path, monkeypatch):
    fake = tmp_path / "fake_generate.py"
    fake.write_text(f"RESULT = {json.dumps(json.dumps(demo_data.DEMO_RESULT))}\n" + FAKE_PIPELINE, encoding="utf-8")
    monkeypatch.setattr(Paths, "generator_command", property(lambda self: [str(fake)]))
    return make_client(workspace)
