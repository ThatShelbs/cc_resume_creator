"""Where Resume Taylor reads and writes. One object, so tests can point it at a
temp directory while still running the real pipeline scripts."""

import os
from dataclasses import dataclass
from pathlib import Path

from .fs import long_path


@dataclass(frozen=True)
class Paths:
    data_root: Path

    def __post_init__(self):
        # Every path derived from here is extended-length on Windows, so a
        # deep data folder can't hit MAX_PATH. Anything handed to Word or
        # shown to the user goes through plain_path() first.
        object.__setattr__(self, "data_root", long_path(Path(self.data_root)))

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
    def secrets_path(self) -> Path:
        return self.data_root / "secrets.json"

    @property
    def sample_marker(self) -> Path:
        return self.data_root / ".sample_data.json"

    @property
    def scratch_dir(self) -> Path:
        return self.data_root / ".taylor_tmp"

    # The pipeline always runs from the code checkout, as `python <these args>`.
    @property
    def generator_command(self) -> list[str]:
        return ["-m", "resume_taylor.pipeline"]

    @property
    def fact_bank_command(self) -> list[str]:
        return ["-m", "resume_taylor.pipeline.build_fact_bank"]

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


def default_data_root() -> Path:
    """Personal data lives outside the code folder so a re-download, `git pull`
    or accidental `git add .` can never touch it (and it stays off OneDrive's
    long paths). RESUME_TAYLOR_DATA overrides; --data-root overrides that."""
    override = (os.environ.get("RESUME_TAYLOR_DATA") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    base = Path(os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share"))
    return base / "ResumeTaylor"


def default_paths() -> Paths:
    return Paths(default_data_root())
