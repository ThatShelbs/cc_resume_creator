"""
Background jobs: every Claude call and every docx/pdf render runs as a
subprocess of the real pipeline scripts, one at a time, on a single worker
thread. The subprocess's output is the progress feed: "::stage <name>" and
"::deny {...}" lines (printed because TAYLOR_PROGRESS=1) are parsed into
structured state, and everything else is kept as the human-readable log that
the UI streams over Server-Sent Events.

Running out-of-process keeps the server responsive and isolated: the
pipeline's module-level WARNINGS list, its sys.exit() error handling, and
Word's COM automation all live and die with the child process, and a hung
call is killed (with its whole process tree) when it hits the timeout.
"""

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import CODE_ROOT, credentials

MAX_LINES = 4000
MAX_JOBS_KEPT = 60

TIMEOUT_HINT = "Claude took longer than the timeout. Try again, or raise the timeout in Settings."

# First match wins, so the specific failures come before the broad sign-in check.
HINTS = [
    (re.compile(r"prohibited claim", re.I),
     "The content matched your never-claim list, so nothing was written. Edit the highlighted text, "
     "or adjust the list under Evidence."),
    (re.compile(r"is locked, most likely open in word", re.I),
     "A file is open in Word. Close it and try again."),
    (re.compile(r"did not respond within", re.I), TIMEOUT_HINT),
    (re.compile(r"could not find the `?claude`? cli", re.I),
     "The Claude Code CLI isn't installed or isn't on PATH. Install it with "
     "`npm install -g @anthropic-ai/claude-code`, then run `claude /login`."),
    (re.compile(r"not logged in|please log in|/login|authenticat|unauthori[sz]ed|\b401\b|invalid api key", re.I),
     "Claude CLI needs you to sign in. Open a terminal and run `claude /login`, then try again."),
    (re.compile(r"usage limit|rate limit|overloaded", re.I),
     "Claude is rate limited right now. Wait a few minutes and try again."),
]


class Job:
    def __init__(self, kind: str, label: str, project_id: str | None):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.label = label
        self.project_id = project_id
        self.status = "queued"  # queued | running | succeeded | failed | cancelled
        # How the subprocess ended. `status` only takes this value after the
        # success/finish callbacks have run, so a client that sees a finished
        # job and refetches always gets the installed results.
        self.outcome: str | None = None
        self.stage = "queued"
        self.stages_seen: list[str] = []
        self.lines: list[str] = []
        self.deny: list[dict] = []
        self.error: str | None = None
        self.hint: str | None = None
        self.returncode: int | None = None
        self.created = datetime.now().isoformat(timespec="seconds")
        self.started: float | None = None
        self.finished: float | None = None
        self.cancel_requested = False
        self.proc: subprocess.Popen | None = None
        self.result: dict | None = None  # optional payload set by on_success

    @property
    def done(self) -> bool:
        return self.status in ("succeeded", "failed", "cancelled")

    def summary(self) -> dict:
        elapsed = None
        if self.started:
            elapsed = round((self.finished or time.time()) - self.started, 1)
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "project_id": self.project_id,
            "status": self.status,
            "stage": self.stage,
            "stages_seen": self.stages_seen,
            "error": self.error,
            "hint": self.hint,
            "deny": self.deny,
            "created": self.created,
            "elapsed": elapsed,
            "line_count": len(self.lines),
            "result": self.result,
        }


class JobManager:
    def __init__(self):
        self._jobs: "OrderedDict[str, Job]" = OrderedDict()
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._loop, name="taylor-jobs", daemon=True)
        self._worker.start()

    # -- public ----------------------------------------------------------------

    def submit(
        self,
        kind: str,
        label: str,
        args: list[str],
        *,
        project_id: str | None = None,
        timeout: int = 900,
        log_path: Path | None = None,
        env: dict | None = None,
        on_success: Callable[[Job], None] | None = None,
        on_finish: Callable[[Job], None] | None = None,
    ) -> Job:
        with self._lock:
            busy = next(
                (j for j in self._jobs.values() if not j.done and project_id and j.project_id == project_id),
                None,
            )
            if busy:
                raise RuntimeError(f"'{busy.label}' is already running for this project.")
            job = Job(kind, label, project_id)
            self._jobs[job.id] = job
            while len(self._jobs) > MAX_JOBS_KEPT:
                oldest = next(iter(self._jobs.values()))
                if not oldest.done:
                    break
                self._jobs.popitem(last=False)
        self._queue.put((job, args, timeout, log_path, env or {}, on_success, on_finish))
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def active(self) -> list[Job]:
        return [j for j in self._jobs.values() if not j.done]

    def latest_for(self, project_id: str) -> Job | None:
        for job in reversed(self._jobs.values()):
            if job.project_id == project_id:
                return job
        return None

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.done:
            return False
        job.cancel_requested = True
        if job.proc and job.proc.poll() is None:
            _kill_tree(job.proc)
        return True

    # -- worker ------------------------------------------------------------------

    def _loop(self) -> None:
        while True:
            job, args, timeout, log_path, extra_env, on_success, on_finish = self._queue.get()
            try:
                if job.cancel_requested:
                    job.outcome = "cancelled"
                    continue
                self._run(job, args, timeout, log_path, extra_env)
                if job.outcome == "succeeded" and on_success:
                    job.stage = "finalizing"
                    try:
                        on_success(job)
                    except Exception as exc:  # surface bookkeeping failures as job failures
                        job.outcome = "failed"
                        job.error = f"The job finished but its results couldn't be saved: {exc}"
            except Exception as exc:  # never let one job kill the worker thread
                job.outcome = "failed"
                job.error = job.error or f"Unexpected error: {exc}"
            finally:
                job.outcome = job.outcome or "failed"
                if on_finish:
                    try:
                        on_finish(job)
                    except Exception:
                        pass
                if job.outcome == "succeeded":
                    job.stage = "done"
                if job.finished is None:
                    job.finished = time.time()
                job.status = job.outcome
                self._queue.task_done()

    def _run(self, job: Job, args: list[str], timeout: int, log_path: Path | None, extra_env: dict) -> None:
        env = {
            **os.environ,
            "TAYLOR_PROGRESS": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
            **extra_env,
        }
        creationflags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
        job.status = "running"
        job.stage = "preparing"
        job.started = time.time()
        log = open(log_path, "w", encoding="utf-8") if log_path else None
        try:
            job.proc = subprocess.Popen(
                [sys.executable, "-u", *args],
                cwd=str(CODE_ROOT),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
        except OSError as exc:
            job.outcome, job.error = "failed", f"Could not start the pipeline: {exc}"
            if log:
                log.close()
            return

        timed_out = threading.Event()

        def on_timeout():
            timed_out.set()
            _kill_tree(job.proc)

        timer = threading.Timer(timeout, on_timeout)
        timer.daemon = True
        timer.start()
        try:
            for raw in job.proc.stdout:
                line = raw.rstrip("\r\n")
                if log:
                    log.write(line + "\n")
                    log.flush()
                self._consume(job, line)
            job.returncode = job.proc.wait()
        finally:
            timer.cancel()
            if log:
                log.close()

        job.finished = time.time()
        if job.cancel_requested:
            job.outcome = "cancelled"
            job.error = "Cancelled."
        elif timed_out.is_set():
            job.outcome = "failed"
            job.error = f"Stopped after {timeout // 60} minutes without finishing."
            job.hint = TIMEOUT_HINT
        elif job.returncode == 0:
            job.outcome = "succeeded"
        else:
            job.outcome = "failed"
            job.error = _last_message(job.lines) or f"The pipeline exited with code {job.returncode}."
            text = "\n".join(job.lines[-60:])
            job.hint = next((hint for rx, hint in HINTS if rx.search(text)), None)

    @staticmethod
    def _consume(job: Job, line: str) -> None:
        if line.startswith("::stage "):
            job.stage = line[len("::stage "):].strip()
            if job.stage not in job.stages_seen:
                job.stages_seen.append(job.stage)
            return
        if line.startswith("::deny "):
            try:
                job.deny.append(json.loads(line[len("::deny "):]))
            except ValueError:
                pass
            return
        # tqdm-style carriage-return progress bars are noise in a log view.
        if "\r" in line:
            line = line.split("\r")[-1]
        if len(job.lines) < MAX_LINES:
            job.lines.append(line)


def _last_message(lines: list[str]) -> str:
    """The error the pipeline exited with (sys.exit prints it last). Keeps a
    short multi-line message together, e.g. 'claude CLI exited with an error:' + detail."""
    tail = [l for l in lines if l.strip()][-4:]
    if not tail:
        return ""
    for i, line in enumerate(tail):
        if line.rstrip().endswith(":") and i < len(tail) - 1:
            return "\n".join(tail[i:]).strip()
    return tail[-1].strip()


def _kill_tree(proc: subprocess.Popen | None) -> None:
    if not proc or proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000,
        )
    else:
        proc.kill()
