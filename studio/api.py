"""
The Resume Studio HTTP API (FastAPI) plus the built React app.

Security model for a local-only app: the server binds to 127.0.0.1, rejects
any request whose Host isn't a loopback name (defeats DNS rebinding), and
requires a random per-launch token on every /api call (injected into the
served index.html, sent back as X-Studio-Token, or as ?t= for plain links
like downloads). A web page in another tab can't read the token, so it can't
drive the API.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import Body, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from . import CODE_ROOT, __version__
from . import facts as facts_mod
from . import lint as lint_mod
from . import profile_store, resume_ingest
from .jobs import Job, JobManager
from .paths import Paths, plain_path, remove_tree
from .projects import STATUSES, NotFound, ProjectError, ProjectStore, file_hash, guess_company_role, now, stamp
from .settings import EFFORT_CHOICES, MODEL_CHOICES, Settings, load_settings, save_settings

import generate_resume as g

MAX_UPLOAD = 20 * 1024 * 1024
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}
DIST_DIR = CODE_ROOT / "webapp" / "frontend" / "dist"
# Reachable without the session token: a liveness probe for the launcher and
# the API docs (schema only, no data).
OPEN_PATHS = {"/api/health", "/api/docs", "/api/openapi.json"}


def _hostname(host_header: str) -> str:
    host = host_header.strip().lower()
    if host.startswith("["):
        return host[: host.find("]") + 1]
    return host.rsplit(":", 1)[0] if ":" in host else host


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class NewProject(BaseModel):
    job_text: str
    company: str = ""
    role: str = ""
    name: str = ""
    url: str = ""
    template: str | None = None
    cover_letter: bool | None = None
    generate: bool = False


class ProjectPatch(BaseModel):
    name: str | None = None
    company: str | None = None
    role: str | None = None
    url: str | None = None
    status: str | None = None
    notes: str | None = None
    applied_on: str | None = None
    template: str | None = None
    cover_letter: bool | None = None


class TextBody(BaseModel):
    text: str


class RenderBody(BaseModel):
    template: str | None = None


class ResumeConfirm(BaseModel):
    structure: resume_ingest.ResumeStructure
    upload_id: str | None = None


class FactsBody(BaseModel):
    facts: list[facts_mod.Fact]


class DraftFactsBody(BaseModel):
    force: bool = False


class PhraseBody(BaseModel):
    text: str
    phrase: str


class ImportBody(BaseModel):
    files: list[str]


class OpenFolderBody(BaseModel):
    target: str = "data"


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(paths: Paths, token: str, *, extra_hosts: set | None = None,
               jobs: JobManager | None = None) -> FastAPI:
    paths.ensure()
    store = ProjectStore(paths.projects_dir, paths.trash_dir)
    jobs = jobs or JobManager()
    allowed_hosts = LOOPBACK_HOSTS | (extra_hosts or set())
    uploads: dict[str, dict] = {}  # upload_id -> {"path": Path, "structure": ...}
    cache: dict = {}

    app = FastAPI(
        title="Resume Studio API",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.paths = paths
    app.state.jobs = jobs
    app.state.store = store

    # -- middleware ------------------------------------------------------------

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if _hostname(request.headers.get("host", "")) not in allowed_hosts:
            return JSONResponse({"detail": "Resume Studio only answers on localhost."}, status_code=421)
        path = request.url.path
        if path.startswith("/api/") and path not in OPEN_PATHS:
            supplied = request.headers.get("x-studio-token") or request.query_params.get("t")
            if supplied != token:
                return JSONResponse({"detail": "Missing or invalid session token. Reload the page."}, status_code=403)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    @app.exception_handler(NotFound)
    async def _not_found(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ProjectError)
    async def _project_error(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    for exc_type in (profile_store.ProfileError, resume_ingest.IngestError, facts_mod.FactBankError):
        app.add_exception_handler(exc_type, lambda _r, exc: JSONResponse({"detail": str(exc)}, status_code=400))

    # -- helpers -----------------------------------------------------------------

    def settings() -> Settings:
        return load_settings(paths.settings_path)

    def profile_path() -> Path | None:
        return paths.latest("in_profile")

    def resume_path() -> Path | None:
        return paths.latest("in_resume")

    def require_inputs() -> tuple[Path, Path]:
        pp, rp = profile_path(), resume_path()
        if not pp:
            raise HTTPException(409, "Add your profile first (Profile page).")
        if not rp:
            raise HTTPException(409, "Upload your base resume first (Base Resume page).")
        return pp, rp

    def companies() -> list[str]:
        rp = resume_path()
        if not rp:
            return []
        try:
            return [j["company"] for j in g.parse_prior_resume(rp)["jobs"]]
        except SystemExit:
            return []

    def current_hashes() -> dict[str, str]:
        return {
            "profile": file_hash(profile_path()),
            "resume": file_hash(resume_path()),
            "fact_bank": file_hash(paths.fact_bank_path),
        }

    def source_context() -> dict:
        """Profile+resume text, fact bank, and deny list for the live linter,
        cached until any of those files change."""
        key = (tuple(current_hashes().values()), file_hash(paths.deny_path))
        if cache.get("ctx_key") != key:
            pp, rp = profile_path(), resume_path()
            text = ""
            try:
                if pp:
                    text += g.read_docx_text(pp)
                if rp:
                    text += "\n" + g.read_docx_text(rp)
            except SystemExit:
                pass
            bank = None
            if paths.fact_bank_path.exists():
                bank = {f.id: f.model_dump() for f in facts_mod.read_facts(paths.fact_bank_path)}
                comps = companies()
                for fact in bank.values():
                    fact["employer"] = g.snap_employer(fact["employer"], comps) or "unassigned"
            try:
                deny = g.load_deny_patterns(paths.deny_path)
            except SystemExit:
                deny = []
            cache["ctx_key"] = key
            cache["ctx"] = {"source_text": text, "fact_bank": bank, "deny": deny}
        return cache["ctx"]

    def project_summary(meta, hashes: dict) -> dict:
        d = store.dir(meta.id)
        outputs = store.outputs(meta.id)
        last = meta.last_generate
        job = jobs.latest_for(meta.id)
        changed = []
        if last and last.ok and last.input_hashes:
            changed = [k for k, v in hashes.items() if last.input_hashes.get(k, "") != v]
        return {
            **meta.model_dump(),
            "has_result": (d / "result.json").exists(),
            "has_pdf": any(f["name"].endswith(".pdf") and f["name"].startswith("out_resume_") for f in outputs),
            "inputs_changed": changed,
            "outputs_stale": bool(meta.result_saved_at and meta.rendered_at and meta.result_saved_at > meta.rendered_at),
            "active_job": job.summary() if job and not job.done else None,
        }

    def pipeline_args(pid: str, staging: Path, s: Settings, meta, *, render: bool) -> list[str]:
        pp, rp = require_inputs()
        d = store.dir(pid)
        # Plain paths (no extended-length prefix): the pipeline hands them to Word.
        d, staging = plain_path(d), plain_path(staging)
        args = [
            str(paths.generator_script),
            "--profile", str(pp),
            "--resume", str(rp),
            "--job", str(d / "job.txt"),
            "--fact-bank", str(paths.fact_bank_path),
            "--deny", str(paths.deny_path),
            "--model", s.model,
            "--effort", s.effort,
            "--template", meta.template,
            "--out-dir", str(staging),
            "--result-json", str(staging / "result.json"),
        ]
        if render:
            args += ["--render-json", str(d / "result.json")]
        elif meta.cover_letter:
            args.append("--cover-letter")
        return args

    def start_pipeline(pid: str, *, render: bool) -> Job:
        meta = store.get(pid)
        s = settings()
        if render and not store.result_path(pid).exists():
            raise HTTPException(409, "Generate this resume first.")
        staging = store.dir(pid) / f".staging-{uuid.uuid4().hex[:8]}"
        staging.mkdir()
        args = pipeline_args(pid, staging, s, meta, render=render)
        kind = "render" if render else "generate"
        started = now()

        def on_success(job: Job) -> None:
            hashes = {}
            if not render:
                hashes = store.snapshot_inputs(pid, {
                    "profile": profile_path(), "resume": resume_path(), "fact_bank": paths.fact_bank_path,
                })
            store.promote(pid, staging, new_version=not render)
            done_at = stamp()
            fields = {"rendered_at": done_at, "result_saved_at": done_at}
            run = {"kind": kind, "when": started, "ok": True, "model": s.model, "effort": s.effort}
            if render:
                fields["last_render"] = run
            else:
                fields["last_generate"] = {**run, "input_hashes": hashes}
            store.touch(pid, **fields)

        def on_finish(job: Job) -> None:
            if job.outcome != "succeeded" and (staging / "result.json").exists():
                # The pipeline finished but installing its output failed: keep
                # the new files rather than throw away a finished draft.
                job.error = f"{job.error} Your new files were kept in {plain_path(staging)}."
            else:
                remove_tree(staging, quiet=True)
            if job.outcome != "succeeded":
                run = {"kind": kind, "when": started, "ok": False, "model": s.model, "effort": s.effort,
                       "error": job.error}
                try:
                    store.touch(pid, **({"last_render": run} if render else {"last_generate": run}))
                except (ProjectError, OSError):
                    pass

        label = "Re-rendering resume" if render else f"Tailoring resume for {meta.name}"
        try:
            return jobs.submit(
                kind, label, args,
                project_id=pid,
                timeout=(240 if render else s.timeout_seconds * 4 + 300),
                log_path=store.dir(pid) / "run.log",
                env={"CLAUDE_TIMEOUT": str(s.timeout_seconds)},
                on_success=on_success,
                on_finish=on_finish,
            )
        except RuntimeError as exc:
            remove_tree(staging, quiet=True)
            raise HTTPException(409, str(exc)) from None

    async def read_upload(file: UploadFile, allowed: tuple) -> tuple[str, bytes]:
        name = Path(file.filename or "upload").name
        ext = Path(name).suffix.lower()
        if ext not in allowed:
            raise HTTPException(400, f"Upload a {' or '.join(allowed)} file.")
        data = await file.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "That file is larger than 20 MB.")
        if not data:
            raise HTTPException(400, "That file is empty.")
        safe = re.sub(r"[^\w.\- ]+", "_", Path(name).stem).strip() or "upload"
        return f"{safe}{ext}", data

    def open_path(target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        target = plain_path(target)
        if sys.platform == "win32":
            os.startfile(str(target))  # noqa: S606 - opening a local folder for the user
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])

    def claude_info() -> dict:
        cached = cache.get("claude")
        if cached and time.time() - cached["at"] < 300:
            return cached["info"]
        path = shutil.which("claude")
        info = {"found": bool(path), "path": path, "version": None}
        if path:
            try:
                out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=20,
                                     creationflags=0x08000000 if sys.platform == "win32" else 0)
                info["version"] = (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else None
            except (OSError, subprocess.TimeoutExpired):
                pass
        cache["claude"] = {"at": time.time(), "info": info}
        return info

    def word_available() -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winreg

            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"))
            return True
        except OSError:
            return False

    # -- system ----------------------------------------------------------------------

    @app.get("/api/health")
    def health():
        return {"app": "resume-studio", "version": __version__}

    @app.get("/api/system")
    def system():
        pp, rp = profile_path(), resume_path()
        fact_count = None
        if paths.fact_bank_path.exists():
            try:
                fact_count = len(facts_mod.read_facts(paths.fact_bank_path))
            except facts_mod.FactBankError:
                fact_count = 0
        deny_count = len([r for r in facts_mod.check_deny_text(facts_mod.read_deny_text(paths.deny_path)) if not r["error"]])
        return {
            "version": __version__,
            "claude": claude_info(),
            "word": word_available(),
            "platform": sys.platform,
            "data_root": str(paths.data_root),
            "inputs": {
                "profile": pp.name if pp else None,
                "resume": rp.name if rp else None,
                "fact_bank": fact_count,
                "deny_patterns": deny_count,
            },
            "onboarding_needed": not (pp and rp),
            "templates": [
                {"key": t.key, "label": t.label, "description": t.description} for t in g.TEMPLATES.values()
            ],
            "statuses": STATUSES,
            "models": MODEL_CHOICES,
            "efforts": EFFORT_CHOICES,
            "active_jobs": [j.summary() for j in jobs.active()],
        }

    @app.get("/api/settings")
    def get_settings():
        return settings()

    @app.put("/api/settings")
    def put_settings(body: Settings):
        save_settings(paths.settings_path, body)
        return body

    @app.post("/api/system/open-folder")
    def open_folder(body: OpenFolderBody):
        targets = {"data": paths.data_root, "inputs": paths.input_dir, "projects": paths.projects_dir,
                   "archive": paths.archive_dir}
        if body.target not in targets:
            raise HTTPException(400, "Unknown folder.")
        open_path(targets[body.target])
        return {"ok": True}

    @app.post("/api/system/shutdown")
    def shutdown():
        def _stop():
            time.sleep(0.5)
            os._exit(0)

        import threading

        threading.Thread(target=_stop, daemon=True).start()
        return {"ok": True}

    # -- profile ---------------------------------------------------------------------

    def profile_payload(path: Path | None, backup: Path | None = None) -> dict:
        if not path:
            return {"exists": False, "file": None, "updated": None, "profile": profile_store.Profile().model_dump()}
        return {
            "exists": True,
            "file": path.name,
            "updated": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            "profile": profile_store.read_profile(path).model_dump(),
            "backup": backup.name if backup else None,
        }

    @app.get("/api/profile")
    def get_profile():
        return profile_payload(profile_path())

    @app.put("/api/profile")
    def put_profile(body: profile_store.Profile):
        path = profile_path() or paths.input_dir / "in_profile.docx"
        backup = profile_store.save_profile(body, path, paths.archive_dir)
        cache.pop("ctx_key", None)
        return profile_payload(path, backup)

    @app.post("/api/profile/import")
    async def import_profile(file: UploadFile = File(...)):
        name, data = await read_upload(file, (".docx",))
        tmp = paths.scratch_dir / f"{uuid.uuid4().hex}_{name}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        try:
            return {"profile": profile_store.read_profile(tmp).model_dump()}
        except Exception as exc:  # python-docx raises several types on bad files
            raise HTTPException(400, f"Couldn't read that Word file ({exc}).") from None
        finally:
            tmp.unlink(missing_ok=True)

    @app.get("/api/profile/download")
    def download_profile():
        path = profile_path()
        if not path:
            raise HTTPException(404, "No profile yet.")
        return FileResponse(path, filename=path.name)

    # -- base resume -------------------------------------------------------------------

    @app.get("/api/resume")
    def get_resume():
        path = resume_path()
        if not path:
            return {"exists": False, "file": None, "updated": None, "structure": None, "originals": []}
        structure = resume_ingest.structure_from_paras(g.docx_paras(path, strip=False))
        structure.source = "current"
        structure.source_file = path.name
        originals = sorted((p.name for p in paths.originals_dir.glob("*") if p.is_file()), reverse=True) \
            if paths.originals_dir.exists() else []
        return {
            "exists": True,
            "file": path.name,
            "updated": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            "structure": structure.model_dump(exclude={"raw_text"}),
            "originals": originals[:10],
        }

    @app.post("/api/resume/upload")
    async def upload_resume(file: UploadFile = File(...)):
        name, data = await read_upload(file, (".pdf", ".docx"))
        paths.originals_dir.mkdir(parents=True, exist_ok=True)
        uploaded_at = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        saved = paths.originals_dir / f"{uploaded_at}_{name}"
        saved.write_bytes(data)
        try:
            structure = resume_ingest.ingest(saved)
        except resume_ingest.IngestError:
            raise
        except Exception as exc:
            raise HTTPException(400, f"Couldn't read that file ({exc}).") from None
        upload_id = uuid.uuid4().hex[:12]
        uploads[upload_id] = {"path": saved}
        return {
            "upload_id": upload_id,
            "structure": structure.model_dump(exclude={"raw_text"}),
            "needs_ai": not structure.jobs,
            "prefill": resume_ingest.prefill_contact(structure),
        }

    @app.post("/api/resume/ai/{upload_id}")
    def structure_with_ai(upload_id: str):
        upload = uploads.get(upload_id)
        if not upload:
            raise HTTPException(404, "Upload the file again.")
        out = paths.scratch_dir / f"structure_{upload_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)

        def on_success(job: Job) -> None:
            structure = resume_ingest.ResumeStructure(**json.loads(out.read_text(encoding="utf-8")))
            job.result = {
                "structure": structure.model_dump(exclude={"raw_text"}),
                "prefill": resume_ingest.prefill_contact(structure),
            }
            out.unlink(missing_ok=True)

        s = settings()
        job = jobs.submit(
            "ingest", "Structuring your resume with Claude",
            ["-m", "studio.resume_ingest", "--ai", str(upload["path"]), "--out", str(out)],
            timeout=s.timeout_seconds * 2 + 60,
            env={"CLAUDE_TIMEOUT": str(s.timeout_seconds)},
            on_success=on_success,
        )
        return job.summary()

    @app.post("/api/resume/confirm")
    def confirm_resume(body: ResumeConfirm):
        resume_ingest.validate_structure(body.structure)
        existing = resume_path()
        contact = None
        pp = profile_path()
        if pp:
            try:
                contact = g.parse_applicant_info(pp)
            except SystemExit:
                contact = None
        suffix = f"{contact['first_name']}-{contact['last_name']}".strip("-") if contact else "base"
        suffix = re.sub(r"[^\w-]+", "-", suffix).strip("-") or "base"
        target = paths.input_dir / f"in_resume_{suffix}.docx"
        if existing:
            profile_store.backup(existing, paths.archive_dir)
            if existing != target:
                existing.unlink()
        resume_ingest.write_resume_docx(body.structure, target)
        cache.pop("ctx_key", None)
        comps = [j.company for j in body.structure.jobs]
        issues = facts_mod.employer_issues(facts_mod.read_facts(paths.fact_bank_path), comps) \
            if paths.fact_bank_path.exists() else []
        return {"file": target.name, "fact_bank_issues": issues}

    @app.get("/api/resume/download")
    def download_resume():
        path = resume_path()
        if not path:
            raise HTTPException(404, "No base resume yet.")
        return FileResponse(path, filename=path.name)

    # -- evidence: fact bank + never-claim list -------------------------------------------

    def facts_payload() -> dict:
        items = facts_mod.read_facts(paths.fact_bank_path)
        comps = companies()
        return {
            "exists": paths.fact_bank_path.exists(),
            "facts": [f.model_dump() for f in items],
            "companies": comps,
            "kinds": facts_mod.FACT_KINDS,
            "employer_issues": facts_mod.employer_issues(items, comps),
        }

    @app.get("/api/facts")
    def get_facts():
        return facts_payload()

    @app.put("/api/facts")
    def put_facts(body: FactsBody):
        if paths.fact_bank_path.exists():
            profile_store.backup(paths.fact_bank_path, paths.archive_dir)
        facts_mod.write_facts(paths.fact_bank_path, body.facts)
        cache.pop("ctx_key", None)
        return facts_payload()

    @app.post("/api/facts/draft")
    def draft_facts(body: DraftFactsBody):
        pp, rp = require_inputs()
        if paths.fact_bank_path.exists() and not body.force:
            raise HTTPException(409, "You already have a fact bank. Confirm to replace it (a backup is kept).")
        if paths.fact_bank_path.exists():
            profile_store.backup(paths.fact_bank_path, paths.archive_dir)
        s = settings()
        args = [str(paths.fact_bank_script), "--profile", str(pp), "--resume", str(rp),
                "--out", str(paths.fact_bank_path)]
        if body.force:
            args.append("--force")
        try:
            job = jobs.submit(
                "fact_bank", "Drafting your fact bank", args,
                timeout=s.timeout_seconds * 3 + 60,
                env={"CLAUDE_TIMEOUT": str(s.timeout_seconds)},
                on_success=lambda _job: cache.pop("ctx_key", None),
            )
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from None
        return job.summary()

    @app.get("/api/guardrails")
    def get_guardrails():
        text = facts_mod.read_deny_text(paths.deny_path)
        return {"text": text, "patterns": facts_mod.check_deny_text(text)}

    @app.put("/api/guardrails")
    def put_guardrails(body: TextBody):
        facts_mod.write_deny_text(paths.deny_path, body.text)
        cache.pop("ctx_key", None)
        return get_guardrails()

    @app.post("/api/guardrails/test")
    def test_guardrails(body: PhraseBody):
        return {"matches": facts_mod.match_phrase(body.text, body.phrase), "patterns": facts_mod.check_deny_text(body.text)}

    # -- projects ---------------------------------------------------------------------------

    @app.get("/api/projects")
    def list_projects():
        hashes = current_hashes()
        return [project_summary(m, hashes) for m in store.all()]

    @app.post("/api/projects/guess")
    def guess(body: TextBody):
        return guess_company_role(body.text)

    @app.post("/api/projects/extract-posting")
    async def extract_posting(file: UploadFile = File(...)):
        name, data = await read_upload(file, (".docx", ".pdf", ".txt", ".md"))
        tmp = paths.scratch_dir / f"{uuid.uuid4().hex}_{name}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        try:
            text = g.read_input_text(tmp)
        except (Exception, SystemExit) as exc:
            raise HTTPException(400, f"Couldn't read text from that file ({exc}).") from None
        finally:
            tmp.unlink(missing_ok=True)
        if not text.strip():
            raise HTTPException(400, "No text could be read from that file (a scanned PDF?). Paste the text instead.")
        return {"text": text, **guess_company_role(text)}

    @app.post("/api/projects")
    def create_project(body: NewProject):
        s = settings()
        meta = store.create(
            job_text=body.job_text,
            company=body.company,
            role=body.role,
            name=body.name,
            url=body.url,
            template=body.template or s.default_template,
            cover_letter=s.cover_letter_default if body.cover_letter is None else body.cover_letter,
        )
        job = start_pipeline(meta.id, render=False).summary() if body.generate else None
        return {"project": project_summary(store.get(meta.id), current_hashes()), "job": job}

    @app.get("/api/projects/{pid}")
    def get_project(pid: str):
        meta = store.get(pid)
        job = jobs.latest_for(pid)
        return {
            "project": project_summary(meta, current_hashes()),
            "job_text": store.get_job_text(pid),
            "result": store.get_result(pid),
            "outputs": store.outputs(pid),
            "job": job.summary() if job else None,
        }

    @app.patch("/api/projects/{pid}")
    def patch_project(pid: str, body: ProjectPatch):
        patch = body.model_dump(exclude_unset=True)
        meta = store.update(pid, patch)
        return project_summary(meta, current_hashes())

    @app.put("/api/projects/{pid}/job")
    def put_job_text(pid: str, body: TextBody):
        store.get(pid)
        store.set_job_text(pid, body.text)
        return project_summary(store.touch(pid), current_hashes())

    @app.put("/api/projects/{pid}/result")
    def put_result(pid: str, result: dict = Body(...)):
        meta = store.save_result(pid, result)
        return project_summary(meta, current_hashes())

    @app.post("/api/projects/{pid}/lint")
    def lint_project(pid: str, result: dict = Body(...)):
        store.get(pid)
        ctx = source_context()
        return lint_mod.lint_result(result, ctx["source_text"], ctx["fact_bank"], ctx["deny"])

    @app.get("/api/projects/{pid}/facts")
    def project_facts(pid: str):
        """Fact text for citation hover cards."""
        store.get(pid)
        return {f.id: {"text": f.text, "employer": f.employer, "kind": f.kind}
                for f in facts_mod.read_facts(paths.fact_bank_path)}

    @app.post("/api/projects/{pid}/generate")
    def generate(pid: str):
        return start_pipeline(pid, render=False).summary()

    @app.post("/api/projects/{pid}/render")
    def render(pid: str, body: RenderBody | None = None):
        if body and body.template:
            store.update(pid, {"template": body.template})
        return start_pipeline(pid, render=True).summary()

    @app.get("/api/projects/{pid}/versions")
    def versions(pid: str):
        return store.versions(pid)

    @app.get("/api/projects/{pid}/versions/{vid}")
    def version(pid: str, vid: str):
        return store.version_result(pid, vid)

    @app.post("/api/projects/{pid}/versions/{vid}/restore")
    def restore_version(pid: str, vid: str):
        restored = store.version_result(pid, vid)
        store.rotate(pid)
        store.save_result(pid, restored)
        if restored.get("template") in g.TEMPLATES:
            store.update(pid, {"template": restored["template"]})
        return start_pipeline(pid, render=True).summary()

    def file_response(path: Path, download: bool) -> FileResponse:
        media = {".pdf": "application/pdf", ".md": "text/markdown; charset=utf-8",
                 ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        return FileResponse(
            path,
            media_type=media.get(path.suffix.lower(), "application/octet-stream"),
            filename=path.name if download else None,
            content_disposition_type="attachment" if download else "inline",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/projects/{pid}/files/{name}")
    def project_file(pid: str, name: str, download: bool = False):
        return file_response(store.safe_file(pid, "outputs", name), download)

    @app.get("/api/projects/{pid}/versions/{vid}/files/{name}")
    def version_file(pid: str, vid: str, name: str, download: bool = True):
        return file_response(store.safe_file(pid, "versions", vid, name), download)

    @app.get("/api/projects/{pid}/report")
    def report(pid: str):
        for f in store.outputs(pid):
            if f["name"].startswith("out_resume_") and f["name"].endswith("_report.md"):
                return PlainTextResponse(store.safe_file(pid, "outputs", f["name"]).read_text(encoding="utf-8"))
        raise HTTPException(404, "No report yet.")

    @app.get("/api/projects/{pid}/log")
    def run_log(pid: str):
        p = store.dir(pid) / "run.log"
        return PlainTextResponse(p.read_text(encoding="utf-8") if p.exists() else "")

    @app.post("/api/projects/{pid}/duplicate")
    def duplicate(pid: str):
        return project_summary(store.duplicate(pid), current_hashes())

    @app.delete("/api/projects/{pid}")
    def delete_project(pid: str):
        job = jobs.latest_for(pid)
        if job and not job.done:
            raise HTTPException(409, "Wait for the running job to finish (or cancel it) before deleting.")
        return {"trash_id": store.trash_project(pid)}

    @app.post("/api/projects/{pid}/open-folder")
    def open_project_folder(pid: str):
        open_path(store.dir(pid))
        return {"ok": True}

    @app.get("/api/trash")
    def trash():
        return store.list_trash()

    @app.post("/api/trash/{tid}/restore")
    def restore(tid: str):
        return project_summary(store.restore(tid), current_hashes())

    # -- importing postings left in resume_input/ by the CLI workflow ----------------

    @app.get("/api/import/candidates")
    def import_candidates():
        imported = {m.imported_from for m in store.all() if m.imported_from}
        if not paths.input_dir.exists():
            return []
        return [
            {"file": p.name, **guess_company_role(_safe_read(p))}
            for p in sorted(paths.input_dir.glob("in_job*"))
            if p.suffix.lower() in g.JOB_POSTING_EXTS and p.name not in imported
        ]

    def _safe_read(p: Path) -> str:
        try:
            return g.read_input_text(p)
        except (Exception, SystemExit):
            return ""

    @app.post("/api/import")
    def import_postings(body: ImportBody):
        created = []
        for name in body.files:
            p = paths.input_dir / Path(name).name
            if not p.exists() or not p.name.startswith("in_job"):
                continue
            text = _safe_read(p)
            if len(text.strip()) < 40:
                continue
            guess_ = guess_company_role(text)
            meta = store.create(job_text=text, company=guess_["company"], role=guess_["role"],
                                template=settings().default_template, imported_from=p.name)
            created.append(meta.id)
        return {"created": created}

    # -- jobs -------------------------------------------------------------------------------

    @app.get("/api/jobs")
    def list_jobs():
        return [j.summary() for j in jobs.active()]

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str, lines: bool = False):
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Unknown job.")
        return {**job.summary(), **({"lines": job.lines} if lines else {})}

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        if not jobs.cancel(job_id):
            raise HTTPException(409, "That job isn't running.")
        return {"ok": True}

    @app.get("/api/jobs/{job_id}/events")
    async def job_events(job_id: str, request: Request):
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Unknown job.")

        def sse(event: str, data) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        async def stream():
            sent = 0
            last_state = None
            last_beat = time.time()
            while True:
                if await request.is_disconnected():
                    return
                batch = job.lines[sent:]
                if batch:
                    sent += len(batch)
                    yield sse("lines", batch)
                state = (job.status, job.stage, len(job.deny))
                if state != last_state:
                    last_state = state
                    yield sse("status", job.summary())
                if job.done and sent >= len(job.lines):
                    yield sse("end", job.summary())
                    return
                if time.time() - last_beat > 15:
                    last_beat = time.time()
                    yield ": keep-alive\n\n"
                await asyncio.sleep(0.25)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    # -- the React app -------------------------------------------------------------------------

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found.")
        dist = DIST_DIR.resolve()
        if full_path:
            candidate = (dist / full_path).resolve()
            if dist in candidate.parents and candidate.is_file():
                headers = {"Cache-Control": "public, max-age=31536000, immutable"} if "/assets/" in f"/{full_path}" else {}
                return FileResponse(candidate, headers=headers)
        index = dist / "index.html"
        if not index.exists():
            return HTMLResponse(
                "<h1>Resume Studio</h1><p>The web app hasn't been built yet. Run "
                "<code>Launch Resume Studio.bat</code> (or <code>npm run build</code> in webapp/frontend).</p>",
                status_code=503,
            )
        html = index.read_text(encoding="utf-8").replace("__STUDIO_TOKEN__", token)
        return HTMLResponse(html, headers={"Cache-Control": "no-store"})

    return app
