"""The per-app state and helpers every route shares.

`create_app()` builds one AppContext and stores it on `app.state.ctx`; route
functions receive it through the `Ctx` dependency instead of closing over it.
"""

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from ..pipeline.factbank import snap_employer
from ..pipeline.guards import load_deny_patterns
from ..pipeline.parsing import parse_prior_resume
from ..pipeline.sources import read_docx_text
from .services.jobs import Job, JobManager
from .services.system import ClaudeStatus
from .storage import credentials
from .storage import facts as facts_mod
from .storage.fs import plain_path, remove_tree
from .storage.paths import Paths
from .storage.projects import ProjectError, ProjectStore, file_hash, now, stamp
from .storage.settings import Settings, load_settings


@dataclass
class AppContext:
    paths: Paths
    token: str
    store: ProjectStore
    jobs: JobManager
    allowed_hosts: set
    claude: ClaudeStatus = field(default_factory=ClaudeStatus)
    uploads: dict[str, dict] = field(default_factory=dict)  # upload_id -> {"path": Path}
    cache: dict = field(default_factory=dict)

    # -- settings and inputs -----------------------------------------------------

    def settings(self) -> Settings:
        return load_settings(self.paths.settings_path)

    def job_env(self, s: Settings) -> dict:
        """Extra environment for a pipeline subprocess: the timeout, plus the
        API key when the user saved one in Settings (else .env or the CLI
        login decides)."""
        env = {"CLAUDE_TIMEOUT": str(s.timeout_seconds)}
        key = credentials.load_key(self.paths.secrets_path)
        if key:
            env["ANTHROPIC_API_KEY"] = key
        return env

    def profile_path(self) -> Path | None:
        return self.paths.latest("in_profile")

    def resume_path(self) -> Path | None:
        return self.paths.latest("in_resume")

    def require_inputs(self) -> tuple[Path, Path]:
        pp, rp = self.profile_path(), self.resume_path()
        if not pp:
            raise HTTPException(409, "Add your profile first (Profile page).")
        if not rp:
            raise HTTPException(409, "Upload your base resume first (Base Resume page).")
        return pp, rp

    def companies(self) -> list[str]:
        rp = self.resume_path()
        if not rp:
            return []
        try:
            return [j["company"] for j in parse_prior_resume(rp)["jobs"]]
        except SystemExit:
            return []

    def current_hashes(self) -> dict[str, str]:
        return {
            "profile": file_hash(self.profile_path()),
            "resume": file_hash(self.resume_path()),
            "fact_bank": file_hash(self.paths.fact_bank_path),
        }

    def source_context(self) -> dict:
        """Profile+resume text, fact bank, and deny list for the live linter,
        cached until any of those files change."""
        cache, paths = self.cache, self.paths
        key = (tuple(self.current_hashes().values()), file_hash(paths.deny_path))
        if cache.get("ctx_key") != key:
            pp, rp = self.profile_path(), self.resume_path()
            text = ""
            try:
                if pp:
                    text += read_docx_text(pp)
                if rp:
                    text += "\n" + read_docx_text(rp)
            except SystemExit:
                pass
            bank = None
            if paths.fact_bank_path.exists():
                bank = {f.id: f.model_dump() for f in facts_mod.read_facts(paths.fact_bank_path)}
                comps = self.companies()
                for fact in bank.values():
                    fact["employer"] = snap_employer(fact["employer"], comps) or "unassigned"
            try:
                deny = load_deny_patterns(paths.deny_path)
            except SystemExit:
                deny = []
            cache["ctx_key"] = key
            cache["ctx"] = {"source_text": text, "fact_bank": bank, "deny": deny}
        return cache["ctx"]

    def invalidate_sources(self) -> None:
        """Call after any change to the profile, resume, fact bank or never-claim list."""
        self.cache.pop("ctx_key", None)

    # -- projects and pipeline runs ------------------------------------------------

    def project_summary(self, meta, hashes: dict) -> dict:
        store = self.store
        d = store.dir(meta.id)
        outputs = store.outputs(meta.id)
        last = meta.last_generate
        job = self.jobs.latest_for(meta.id)
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

    def pipeline_args(self, pid: str, staging: Path, s: Settings, meta, *, render: bool) -> list[str]:
        pp, rp = self.require_inputs()
        paths = self.paths
        d = self.store.dir(pid)
        # Plain paths (no extended-length prefix): the pipeline hands them to Word.
        d, staging = plain_path(d), plain_path(staging)
        args = [
            *paths.generator_command,
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

    def start_pipeline(self, pid: str, *, render: bool) -> Job:
        store, paths, jobs = self.store, self.paths, self.jobs
        meta = store.get(pid)
        s = self.settings()
        if render and not store.result_path(pid).exists():
            raise HTTPException(409, "Generate this resume first.")
        staging = store.dir(pid) / f".staging-{uuid.uuid4().hex[:8]}"
        staging.mkdir()
        args = self.pipeline_args(pid, staging, s, meta, render=render)
        kind = "render" if render else "generate"
        started = now()

        def on_success(job: Job) -> None:
            hashes = {}
            if not render:
                hashes = store.snapshot_inputs(pid, {
                    "profile": self.profile_path(), "resume": self.resume_path(), "fact_bank": paths.fact_bank_path,
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
                env=self.job_env(s),
                on_success=on_success,
                on_finish=on_finish,
            )
        except RuntimeError as exc:
            remove_tree(staging, quiet=True)
            raise HTTPException(409, str(exc)) from None


def get_context(request: Request) -> AppContext:
    return request.app.state.ctx


Ctx = Annotated[AppContext, Depends(get_context)]
