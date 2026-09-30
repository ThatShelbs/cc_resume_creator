"""Sample data for trying the app: a fictional applicant (see
examples/demo_data.py), her profile, base resume, fact bank and three job
projects, two of them already rendered through the real pipeline. No Claude
calls and nothing personal.

Loading into a real data folder is only allowed while that folder has no
profile or resume of its own, and a marker file records what was seeded so
"Clear sample data" removes exactly that and refuses (or backs up first)
if the user has since edited it."""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import CODE_ROOT
from .paths import Paths, plain_path, remove_tree

sys.path.insert(0, str(CODE_ROOT / "examples"))

from demo_data import DEMO_RESULT, FACT_BANK, JOBS, PROFILE, RESUME  # noqa: E402

from .projects import ProjectStore, file_hash, now  # noqa: E402

SEEDED = {"lumen": "modern", "tailspin": "classic"}


class SampleError(Exception):
    pass


def _write_docx(paragraphs: list, path: Path) -> None:
    import docx

    d = docx.Document()
    for text, style in paragraphs:
        d.add_paragraph(text, style=style)
    d.save(str(path))


def _render(paths: Paths, store: ProjectStore, pid: str, template: str) -> None:
    d = plain_path(store.dir(pid))
    cmd = [
        sys.executable, str(paths.generator_script),
        "--profile", str(plain_path(paths.latest("in_profile"))),
        "--resume", str(plain_path(paths.latest("in_resume"))),
        "--job", str(d / "job.txt"),
        "--fact-bank", str(plain_path(paths.fact_bank_path)),
        "--deny", str(plain_path(paths.deny_path)),
        "--render-json", str(d / "result.json"),
        "--result-json", str(d / "result.json"),
        "--out-dir", str(d / "outputs"),
        "--template", template,
    ]
    subprocess.run(cmd, check=True, cwd=str(CODE_ROOT), stdout=subprocess.DEVNULL,
                   creationflags=0x08000000 if sys.platform == "win32" else 0)


def seed_workspace(paths: Paths, log=print) -> dict:
    """Write the sample inputs and projects into `paths`. Returns the files
    written (relative to the data root) so they can be tracked."""
    paths.ensure()
    _write_docx(PROFILE, paths.input_dir / "in_profile.docx")
    _write_docx(RESUME, paths.input_dir / "in_resume_Jordan-Rivera.docx")
    paths.fact_bank_path.write_text(FACT_BANK, encoding="utf-8")
    if not paths.deny_path.exists():
        shutil.copy(CODE_ROOT / "do_not_claim.example.txt", paths.deny_path)

    store = ProjectStore(paths.projects_dir, paths.trash_dir)
    hashes = {
        "profile": file_hash(paths.latest("in_profile")),
        "resume": file_hash(paths.latest("in_resume")),
        "fact_bank": file_hash(paths.fact_bank_path),
    }
    project_ids = []
    for key, job in JOBS.items():
        meta = store.create(job_text=job["text"], company=job["company"], role=job["role"],
                            template=SEEDED.get(key, "classic"))
        project_ids.append(meta.id)
        store.update(meta.id, {"status": job["status"],
                               **({"applied_on": "2026-09-22"} if job["status"] != "draft" else {})})
        if key not in SEEDED:
            continue
        result = copy.deepcopy(DEMO_RESULT)
        if key == "tailspin":
            # Same true facts, different emphasis for a customer-insights role.
            nw = result["experience"][0]["bullets"]
            result["experience"][0]["bullets"] = [nw[2], nw[3], nw[1], nw[0]]
            result["summary"] = (
                "Analytics leader with 11 years of experience in customer segmentation, churn modeling, and forecasting. "
                "Built a churn model that cut churn 12% in one year and store-level forecasts that reduced stockouts 18%, "
                "and currently leads a team of 7 analysts and data scientists."
            )
        (store.dir(meta.id) / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        _render(paths, store, meta.id, SEEDED[key])
        stamp = now()
        store.touch(
            meta.id, rendered_at=stamp, result_saved_at=stamp,
            last_generate={"kind": "generate", "when": stamp, "ok": True, "model": "sonnet", "effort": "medium",
                           "input_hashes": hashes},
        )
        log(f"Seeded {meta.id} ({SEEDED[key]})")
    return {"projects": project_ids, "hashes": hashes}


# -- in-app loading and clearing ---------------------------------------------------


def is_loaded(paths: Paths) -> bool:
    return paths.sample_marker.exists()


def load_sample(paths: Paths) -> dict:
    if is_loaded(paths):
        raise SampleError("Sample data is already loaded.")
    if paths.latest("in_profile") or paths.latest("in_resume"):
        raise SampleError("You already have your own profile or resume, so sample data was not added.")
    if any(p for p in paths.projects_dir.glob("*") if p.is_dir() and not p.name.startswith("_")):
        raise SampleError("You already have projects, so sample data was not added.")
    info = seed_workspace(paths, log=lambda _m: None)
    paths.sample_marker.write_text(json.dumps({"loaded": now(), **info}), encoding="utf-8")
    return info


def _current_hashes(paths: Paths) -> dict:
    return {
        "profile": file_hash(paths.latest("in_profile")),
        "resume": file_hash(paths.latest("in_resume")),
        "fact_bank": file_hash(paths.fact_bank_path),
    }


def clear_sample(paths: Paths) -> dict:
    """Remove the sample inputs and projects. If the user edited any of it,
    everything is first copied to resume_archive/sample_backup_<time>/."""
    if not is_loaded(paths):
        raise SampleError("No sample data is loaded.")
    marker = json.loads(paths.sample_marker.read_text(encoding="utf-8"))
    edited = _current_hashes(paths) != marker.get("hashes")
    store = ProjectStore(paths.projects_dir, paths.trash_dir)
    backup = None
    if edited:
        backup = paths.archive_dir / f"sample_backup_{datetime.now():%Y-%m-%d-%H-%M-%S}"
        backup.mkdir(parents=True, exist_ok=True)
        if paths.input_dir.exists():
            shutil.copytree(paths.input_dir, backup / "resume_input", dirs_exist_ok=True)
    for f in list(paths.input_dir.glob("in_profile*")) + list(paths.input_dir.glob("in_resume*")):
        f.unlink(missing_ok=True)
    paths.fact_bank_path.unlink(missing_ok=True)
    for pid in marker.get("projects", []):
        d = store.dir(pid)
        if d.exists():
            if backup:
                shutil.copytree(d, backup / "projects" / pid, dirs_exist_ok=True)
            remove_tree(d, quiet=True)
    paths.sample_marker.unlink(missing_ok=True)
    return {"cleared": True, "backup": str(plain_path(backup)) if backup else None}
