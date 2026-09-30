"""
Build a self-contained demo workspace (default: ./demo_workspace) around the
fictional persona in examples/demo_data.py: profile, base resume, fact bank,
never-claim list, and three projects at different stages. Two come with a
hand-written (truthful to the persona) result rendered through the real
pipeline, so the app looks lived-in without any Claude calls.

    python scripts/make_demo_workspace.py
    python launcher.py --data-root demo_workspace
"""

import argparse
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))

import docx  # noqa: E402

from demo_data import DEMO_RESULT, FACT_BANK, JOBS, PROFILE, RESUME  # noqa: E402
from studio.paths import Paths, plain_path, remove_tree  # noqa: E402
from studio.projects import ProjectStore, file_hash, now  # noqa: E402


def write_docx(paragraphs: list, path: Path) -> None:
    d = docx.Document()
    for text, style in paragraphs:
        d.add_paragraph(text, style=style)
    d.save(str(path))


def render(paths: Paths, store: ProjectStore, pid: str, template: str) -> None:
    d = plain_path(store.dir(pid))
    out = d / "outputs"
    cmd = [
        sys.executable, str(paths.generator_script),
        "--profile", str(paths.latest("in_profile")),
        "--resume", str(paths.latest("in_resume")),
        "--job", str(d / "job.txt"),
        "--fact-bank", str(paths.fact_bank_path),
        "--deny", str(paths.deny_path),
        "--render-json", str(d / "result.json"),
        "--result-json", str(d / "result.json"),
        "--out-dir", str(out),
        "--template", template,
    ]
    subprocess.run(cmd, check=True, cwd=str(ROOT), stdout=subprocess.DEVNULL)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", type=Path, default=ROOT / "demo_workspace")
    parser.add_argument("--force", action="store_true", help="replace an existing demo workspace")
    args = parser.parse_args()

    target = args.out.resolve()
    if target.exists():
        if not args.force:
            sys.exit(f"{target} exists. Re-run with --force to rebuild it.")
        remove_tree(target)
    paths = Paths(target)
    paths.ensure()

    write_docx(PROFILE, paths.input_dir / "in_profile.docx")
    write_docx(RESUME, paths.input_dir / "in_resume_Jordan-Rivera.docx")
    paths.fact_bank_path.write_text(FACT_BANK, encoding="utf-8")
    shutil.copy(ROOT / "do_not_claim.txt", paths.deny_path)

    store = ProjectStore(paths.projects_dir, paths.trash_dir)
    hashes = {
        "profile": file_hash(paths.latest("in_profile")),
        "resume": file_hash(paths.latest("in_resume")),
        "fact_bank": file_hash(paths.fact_bank_path),
    }
    seeded = {"lumen": "modern", "tailspin": "classic"}
    for key, job in JOBS.items():
        meta = store.create(job_text=job["text"], company=job["company"], role=job["role"],
                            template=seeded.get(key, "classic"))
        store.update(meta.id, {"status": job["status"], **({"applied_on": "2026-09-22"} if job["status"] != "draft" else {})})
        if key not in seeded:
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
        render(paths, store, meta.id, seeded[key])
        stamp = now()
        store.touch(
            meta.id,
            rendered_at=stamp,
            result_saved_at=stamp,
            last_generate={"kind": "generate", "when": stamp, "ok": True, "model": "sonnet", "effort": "medium",
                           "input_hashes": hashes},
        )
        print(f"Seeded {meta.id} ({seeded[key]})")
    print(f"Demo workspace ready at {target}\nRun: python launcher.py --data-root {target.name}")


if __name__ == "__main__":
    main()
