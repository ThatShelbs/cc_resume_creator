"""What the app reports about the machine it runs on: the Claude CLI's install and
sign-in state, whether Word is available for PDF export, and opening folders."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from ...claude_cli import claude_path
from ...subproc import NO_WINDOW
from ..storage.fs import plain_path


class ClaudeStatus:
    """Whether the `claude` CLI is installed and signed in, cached briefly so the
    status endpoints stay fast."""

    def __init__(self) -> None:
        self._cache: dict = {}

    def info(self) -> dict:
        cached = self._cache.get("claude")
        if cached and time.time() - cached["at"] < 300:
            return cached["info"]
        path = claude_path()
        info = {"found": bool(path), "path": path, "version": None}
        if path:
            try:
                out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=20,
                                     creationflags=NO_WINDOW)
                info["version"] = (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else None
            except (OSError, subprocess.TimeoutExpired):
                pass
        self._cache["claude"] = {"at": time.time(), "info": info}
        return info

    def login(self) -> dict:
        """Whether the CLI is signed in (`claude auth status`). Short cache so
        the banner clears soon after the user signs in."""
        cached = self._cache.get("login")
        if cached and time.time() - cached["at"] < 20:
            return cached["info"]
        info = {"logged_in": None, "method": None}
        path = claude_path()
        if path:
            try:
                out = subprocess.run([path, "auth", "status"], capture_output=True, text=True, timeout=20,
                                     creationflags=NO_WINDOW)
                data = json.loads(out.stdout or "{}")
                info = {"logged_in": bool(data.get("loggedIn")), "method": data.get("authMethod")}
            except (OSError, subprocess.TimeoutExpired, ValueError):
                pass
        self._cache["login"] = {"at": time.time(), "info": info}
        return info

    def forget_login(self) -> None:
        self._cache.pop("login", None)


def word_available() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"))
        return True
    except OSError:
        return False


def open_path(target: Path) -> None:
    """Open a folder in the system file manager, creating it first if needed."""
    target.mkdir(parents=True, exist_ok=True)
    target = plain_path(target)
    if sys.platform == "win32":
        os.startfile(str(target))  # noqa: S606 - opening a local folder for the user
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])
