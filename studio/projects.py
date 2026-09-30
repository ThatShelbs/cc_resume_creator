"""
One folder per job application under projects/:

    <id>/project.json     metadata (company, role, status, template, last run, ...)
    <id>/job.txt          the pasted posting
    <id>/result.json      the editable generated content (generate_resume.py --result-json)
    <id>/outputs/         current .docx/.pdf/_report.md (and cover letter)
    <id>/versions/<ts>/   what outputs/ + result.json held before each new generation
    <id>/inputs_snapshot/ the profile/resume/fact bank the last generation used
    <id>/run.log          output of the most recent job

Deleting moves a project to projects/_trash/, from where it can be restored.
"""

import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

import generate_resume as g

from .paths import long_path, remove_tree

STATUSES = ["draft", "applied", "interviewing", "offer", "rejected", "archived"]
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,120}$")


class LastRun(BaseModel):
    kind: str  # "generate" | "render"
    when: str
    ok: bool
    model: str | None = None
    effort: str | None = None
    error: str | None = None
    input_hashes: dict[str, str] = {}


class ProjectMeta(BaseModel):
    id: str
    name: str
    company: str = ""
    role: str = ""
    url: str = ""
    status: str = "draft"
    notes: str = ""
    applied_on: str | None = None
    template: str = g.DEFAULT_TEMPLATE
    cover_letter: bool = False
    created_at: str
    updated_at: str
    result_saved_at: str | None = None
    rendered_at: str | None = None
    last_generate: LastRun | None = None
    last_render: LastRun | None = None
    imported_from: str | None = None


EDITABLE_FIELDS = {"name", "company", "role", "url", "status", "notes", "applied_on", "template", "cover_letter"}


class ProjectError(ValueError):
    pass


class NotFound(ProjectError):
    pass


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def stamp() -> str:
    """Millisecond timestamp for ordering edits against renders, which can
    happen within the same second."""
    return datetime.now().isoformat(timespec="milliseconds")


def slugify(text: str, limit: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].strip("-") or "project"


def file_hash(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def guess_company_role(job_text: str) -> dict:
    """Best-effort prefill for the new-project form; the user confirms it."""
    lines = [l.strip() for l in job_text.splitlines() if l.strip()]
    role, company = "", ""
    for line in lines[:8]:
        m = re.match(r"^(?:job\s+)?title\s*[:\-]\s*(.+)$", line, re.I)
        if m:
            role = m.group(1)
        m = re.match(r"^(?:company|employer|organization)\s*[:\-]\s*(.+)$", line, re.I)
        if m:
            company = m.group(1)
    if lines and not role and len(lines[0]) <= 90:
        first = lines[0]
        m = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", first) or re.match(r"^(.+?)\s+(?:at|@|-|–|\|)\s+(.+)$", first)
        if m:
            role, company = role or m.group(1), company or m.group(2)
        else:
            role = first
    if not company:
        m = re.search(r"\babout\s+([A-Z][\w&.,' -]{1,40}?)(?:\n|:|\s+is\b|\s+we\b)", job_text)
        if m:
            company = m.group(1).strip(" ,.")
    return {"company": company.strip()[:80], "role": role.strip()[:120]}


class ProjectStore:
    def __init__(self, projects_dir: Path, trash_dir: Path):
        # Extended-length paths so deep repo locations can't hit MAX_PATH.
        self.root = long_path(projects_dir)
        self.trash = long_path(trash_dir)

    # -- paths ---------------------------------------------------------------

    def dir(self, pid: str, must_exist: bool = True) -> Path:
        if not ID_RE.match(pid or ""):
            raise NotFound("Unknown project.")
        d = (self.root / pid).resolve()
        if d.parent != self.root.resolve():
            raise NotFound("Unknown project.")
        if must_exist and not (d / "project.json").exists():
            raise NotFound("Unknown project.")
        return d

    def safe_file(self, pid: str, *parts: str) -> Path:
        """A file directly inside one of a project's subfolders (e.g.
        "outputs", or "versions", <id>). Refuses anything with a path
        separator or "..", so it can't reach project.json or escape."""
        if not parts or any(not p or p in (".", "..") or "/" in p or "\\" in p for p in parts):
            raise NotFound("File not found.")
        folder = self.dir(pid).joinpath(*parts[:-1]).resolve()
        target = (folder / parts[-1]).resolve()
        if target.parent != folder or not target.is_file():
            raise NotFound("File not found.")
        return target

    # -- metadata ------------------------------------------------------------

    def _write_meta(self, meta: ProjectMeta) -> None:
        d = self.dir(meta.id, must_exist=False)
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / "project.json.tmp"
        tmp.write_text(meta.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, d / "project.json")

    def get(self, pid: str) -> ProjectMeta:
        d = self.dir(pid)
        return ProjectMeta(**json.loads((d / "project.json").read_text(encoding="utf-8")))

    def all(self) -> list[ProjectMeta]:
        if not self.root.exists():
            return []
        metas = []
        for d in self.root.iterdir():
            if d.name.startswith(("_", ".")) or not (d / "project.json").exists():
                continue
            try:
                metas.append(self.get(d.name))
            except (ValueError, OSError, ProjectError):
                continue
        return sorted(metas, key=lambda m: m.updated_at, reverse=True)

    def _new_id(self, company: str, role: str) -> str:
        base = f"{datetime.now():%Y-%m-%d}_{slugify(f'{company} {role}'.strip() or 'project', 44)}"
        pid, n = base, 2
        while (self.root / pid).exists() or (self.trash / pid).exists():
            pid, n = f"{base}-{n}", n + 1
        return pid

    def create(self, *, job_text: str, company: str = "", role: str = "", name: str = "", url: str = "",
               template: str = g.DEFAULT_TEMPLATE, cover_letter: bool = False,
               imported_from: str | None = None) -> ProjectMeta:
        job_text = job_text.strip()
        if len(job_text) < 40:
            raise ProjectError("Paste the full job posting (it looks too short to tailor against).")
        pid = self._new_id(company, role)
        stamp = now()
        meta = ProjectMeta(
            id=pid,
            name=name.strip() or " at ".join(p for p in (role.strip(), company.strip()) if p) or "Untitled role",
            company=company.strip(),
            role=role.strip(),
            url=url.strip(),
            template=template if template in g.TEMPLATES else g.DEFAULT_TEMPLATE,
            cover_letter=cover_letter,
            created_at=stamp,
            updated_at=stamp,
            imported_from=imported_from,
        )
        self._write_meta(meta)
        self.set_job_text(pid, job_text)
        return meta

    def update(self, pid: str, patch: dict) -> ProjectMeta:
        meta = self.get(pid)
        data = meta.model_dump()
        for key, value in patch.items():
            if key not in EDITABLE_FIELDS:
                continue
            if key == "status" and value not in STATUSES:
                raise ProjectError(f"Unknown status '{value}'.")
            if key == "template" and value not in g.TEMPLATES:
                raise ProjectError(f"Unknown template '{value}'.")
            if key == "name" and not str(value).strip():
                raise ProjectError("A project needs a name.")
            data[key] = value.strip() if isinstance(value, str) else value
        data["updated_at"] = now()
        meta = ProjectMeta(**data)
        self._write_meta(meta)
        return meta

    def touch(self, pid: str, **fields) -> ProjectMeta:
        meta = self.get(pid)
        data = {**meta.model_dump(), **fields, "updated_at": now()}
        meta = ProjectMeta(**data)
        self._write_meta(meta)
        return meta

    # -- job posting and result ----------------------------------------------

    def job_path(self, pid: str) -> Path:
        return self.dir(pid) / "job.txt"

    def get_job_text(self, pid: str) -> str:
        p = self.job_path(pid)
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def set_job_text(self, pid: str, text: str) -> None:
        text = text.strip()
        if len(text) < 40:
            raise ProjectError("Paste the full job posting (it looks too short to tailor against).")
        (self.dir(pid, must_exist=False) / "job.txt").write_text(text + "\n", encoding="utf-8")

    def result_path(self, pid: str) -> Path:
        return self.dir(pid) / "result.json"

    def get_result(self, pid: str) -> dict | None:
        p = self.result_path(pid)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def save_result(self, pid: str, result: dict) -> ProjectMeta:
        for key in ("contact", "summary", "experience", "skills"):
            if key not in result:
                raise ProjectError(f"Result is missing '{key}'.")
        g.save_result(result, self.result_path(pid))
        return self.touch(pid, result_saved_at=stamp())

    # -- outputs and versions ------------------------------------------------

    @staticmethod
    def _files(d: Path) -> list[dict]:
        if not d.exists():
            return []
        out = []
        for f in sorted(d.iterdir()):
            if f.is_file() and not f.name.endswith(".tmp"):
                st = f.stat()
                out.append({"name": f.name, "size": st.st_size,
                            "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")})
        return out

    def outputs(self, pid: str) -> list[dict]:
        return self._files(self.dir(pid) / "outputs")

    def versions(self, pid: str) -> list[dict]:
        vdir = self.dir(pid) / "versions"
        if not vdir.exists():
            return []
        items = []
        for d in sorted((p for p in vdir.iterdir() if p.is_dir()), reverse=True):
            info = {"id": d.name, "files": self._files(d), "template": None, "generated_at": None,
                    "page_count": None, "summary": "", "warnings": 0}
            rp = d / "result.json"
            if rp.exists():
                try:
                    r = json.loads(rp.read_text(encoding="utf-8"))
                    info.update(template=r.get("template"), generated_at=r.get("generated_at"),
                                page_count=r.get("page_count"), summary=r.get("summary", "")[:240],
                                warnings=len(r.get("warnings") or []))
                except (OSError, ValueError):
                    pass
            items.append(info)
        return items

    def version_result(self, pid: str, vid: str) -> dict:
        if not re.match(r"^[\w-]+$", vid):
            raise NotFound("Unknown version.")
        rp = self.dir(pid) / "versions" / vid / "result.json"
        if not rp.exists():
            raise NotFound("Unknown version.")
        return json.loads(rp.read_text(encoding="utf-8"))

    def rotate(self, pid: str) -> str | None:
        """Move the current outputs + result into versions/<timestamp>/."""
        d = self.dir(pid)
        out, result = d / "outputs", d / "result.json"
        if not (result.exists() or (out.exists() and any(out.iterdir()))):
            return None
        vid = datetime.now().strftime("%Y%m%d-%H%M%S")
        vdir = d / "versions" / vid
        n = 2
        while vdir.exists():
            vdir = d / "versions" / f"{vid}-{n}"
            n += 1
        vdir.mkdir(parents=True)
        # Copy everything first and only then clear outputs/, so a failure
        # part-way leaves the current version untouched.
        try:
            if result.exists():
                shutil.copy2(result, vdir / "result.json")
            # PDFs are regenerable from the .docx; keep the convention of
            # archiving .docx + report only.
            keep = [f for f in out.iterdir() if f.suffix.lower() != ".pdf"] if out.exists() else []
            for f in keep:
                shutil.copy2(f, vdir / f.name)
        except OSError:
            remove_tree(vdir, quiet=True)
            raise
        if out.exists():
            for f in out.iterdir():
                f.unlink()
        return vdir.name

    def promote(self, pid: str, staging: Path, new_version: bool) -> None:
        """Install a finished job's outputs. A generation keeps what it
        replaces as a version; a re-render just replaces the files."""
        d = self.dir(pid)
        if new_version:
            self.rotate(pid)
        out = d / "outputs"
        out.mkdir(exist_ok=True)
        for f in out.iterdir():
            f.unlink()
        for f in staging.iterdir():
            if f.name == "result.json":
                shutil.move(str(f), str(d / "result.json"))
            elif f.is_file():
                shutil.move(str(f), str(out / f.name))
        remove_tree(staging, quiet=True)

    def snapshot_inputs(self, pid: str, inputs: dict[str, Path | None]) -> dict[str, str]:
        snap = self.dir(pid) / "inputs_snapshot"
        remove_tree(snap)
        snap.mkdir()
        hashes = {}
        for key, path in inputs.items():
            hashes[key] = file_hash(path)
            if path and path.exists():
                shutil.copy2(path, snap / path.name)
        return hashes

    # -- lifecycle -------------------------------------------------------------

    def duplicate(self, pid: str) -> ProjectMeta:
        src = self.get(pid)
        meta = self.create(
            job_text=self.get_job_text(pid),
            company=src.company,
            role=src.role,
            name=f"{src.name} (copy)",
            url=src.url,
            template=src.template,
            cover_letter=src.cover_letter,
        )
        result = self.get_result(pid)
        if result:
            self.save_result(meta.id, result)
        return self.get(meta.id)

    def trash_project(self, pid: str) -> str:
        d = self.dir(pid)
        self.trash.mkdir(parents=True, exist_ok=True)
        dest = self.trash / d.name
        if dest.exists():
            dest = self.trash / f"{d.name}-{datetime.now():%H%M%S}"
        shutil.move(str(d), str(dest))
        return dest.name

    def list_trash(self) -> list[dict]:
        if not self.trash.exists():
            return []
        items = []
        for d in self.trash.iterdir():
            meta_path = d / "project.json"
            if d.is_dir() and meta_path.exists():
                try:
                    m = json.loads(meta_path.read_text(encoding="utf-8"))
                    items.append({"id": d.name, "name": m.get("name", d.name), "company": m.get("company", ""),
                                  "deleted": datetime.fromtimestamp(d.stat().st_mtime).isoformat(timespec="seconds")})
                except (OSError, ValueError):
                    continue
        return sorted(items, key=lambda i: i["deleted"], reverse=True)

    def restore(self, trash_id: str) -> ProjectMeta:
        if not ID_RE.match(trash_id or ""):
            raise NotFound("Unknown project.")
        src = self.trash / trash_id
        if not (src / "project.json").exists():
            raise NotFound("That project is no longer in the trash.")
        meta = json.loads((src / "project.json").read_text(encoding="utf-8"))
        pid = meta["id"]
        if (self.root / pid).exists():
            pid = self._new_id(meta.get("company", ""), meta.get("role", ""))
        shutil.move(str(src), str(self.root / pid))
        return self.touch(pid, id=pid)
