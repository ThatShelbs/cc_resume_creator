"""Windows-safe filesystem helpers: extended-length paths (deep OneDrive folders),
deleting inside OneDrive-synced folders, and the plain form for other programs."""

import os
import shutil
import stat
import sys
import time
from pathlib import Path

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

    def clear_and_retry(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    p = long_path(p)  # files deeper than MAX_PATH can't be deleted otherwise
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
