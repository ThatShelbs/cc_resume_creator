"""Where the studio reads and writes. One object, so tests can point it at a
temp directory while still running the real pipeline scripts."""

import sys
from dataclasses import dataclass
from pathlib import Path

from . import CODE_ROOT

_LONG_PREFIX = "\\\\?\\"


def long_path(p: Path) -> Path:
    """On Windows, the extended-length form of an absolute path. A project's
    archived versions nest a few folders deep with the pipeline's long file
    names, which can pass the 260-character MAX_PATH limit when the repo
    itself lives in a deep folder (e.g. under OneDrive)."""
    if sys.platform != "win32":
        return p
    s = str(p.resolve())
    return p if s.startswith(_LONG_PREFIX) or s.startswith("\\\\") else Path(_LONG_PREFIX + s)


def remove_tree(p: Path, quiet: bool = False) -> None:
    """shutil.rmtree that also works inside OneDrive-synced folders, which
    mark directories read-only and briefly hold handles while syncing."""
    import os
    import shutil
    import stat
    import time

    def clear_and_retry(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    for attempt in range(5):
        try:
            if p.exists():
                handler = {"onexc" if sys.version_info >= (3, 12) else "onerror": clear_and_retry}
                shutil.rmtree(p, **handler)
            return
        except OSError:
            if attempt == 4:
                if quiet:
                    return
                raise
            time.sleep(0.4)


def plain_path(p: Path) -> Path:
    """The ordinary form, for handing to other programs (Word, subprocesses,
    Explorer), some of which don't understand the \\\\?\\ prefix."""
    s = str(p)
    return Path(s[len(_LONG_PREFIX):]) if s.startswith(_LONG_PREFIX) else p


@dataclass(frozen=True)
class Paths:
    data_root: Path

    @property
    def input_dir(self) -> Path:
        return self.data_root / "resume_input"

    @property
    def archive_dir(self) -> Path:
        return self.data_root / "resume_archive"

    @property
    def originals_dir(self) -> Path:
        return self.input_dir / "originals"

    @property
    def projects_dir(self) -> Path:
        return self.data_root / "projects"

    @property
    def trash_dir(self) -> Path:
        return self.projects_dir / "_trash"

    @property
    def fact_bank_path(self) -> Path:
        return self.input_dir / "fact_bank.yaml"

    @property
    def deny_path(self) -> Path:
        return self.data_root / "do_not_claim.txt"

    @property
    def settings_path(self) -> Path:
        return self.data_root / "app_settings.json"

    @property
    def scratch_dir(self) -> Path:
        return self.data_root / ".studio_tmp"

    # The pipeline scripts always come from the code checkout.
    @property
    def generator_script(self) -> Path:
        return CODE_ROOT / "generate_resume.py"

    @property
    def fact_bank_script(self) -> Path:
        return CODE_ROOT / "build_fact_bank.py"

    def latest(self, prefix: str, exts: tuple = (".docx",)) -> Path | None:
        """Newest resume_input/<prefix>* by modification time, like find_latest()."""
        if not self.input_dir.exists():
            return None
        candidates = [
            p for p in self.input_dir.glob(f"{prefix}*") if p.is_file() and p.suffix.lower() in exts
        ]
        return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None

    def ensure(self) -> None:
        for d in (self.input_dir, self.archive_dir, self.projects_dir):
            d.mkdir(parents=True, exist_ok=True)


def default_paths() -> Paths:
    return Paths(CODE_ROOT)
