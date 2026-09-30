"""Plain-English health check for Resume Taylor (run by Doctor.bat).

Prints what is installed and what is missing, with your user name and folders
hidden, so the output is safe to paste into a bug report.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The doctor must work even when the package isn't installed (that may be the very problem).
sys.path.insert(0, str(ROOT / "backend" / "src"))

HOME = str(Path.home())


def hide(text: str) -> str:
    return str(text).replace(HOME, "~").replace(os.environ.get("USERNAME", "\0"), "<user>")


def line(ok: bool | None, label: str, detail: str = "") -> None:
    mark = {True: "[ OK ]", False: "[FAIL]", None: "[ ?? ]"}[ok]
    print(f"{mark} {label}" + (f"  {hide(detail)}" if detail else ""))


def run(cmd: list[str], timeout: int = 20) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (out.stdout or out.stderr).strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def main() -> int:
    print("Resume Taylor doctor\n")
    problems = 0

    ok = sys.version_info >= (3, 10)
    line(ok, "Python 3.10 or newer", sys.version.split()[0])
    problems += not ok

    venv = ROOT / ".venv" / "Scripts" / "python.exe"
    line(venv.exists(), "Private Python environment (.venv)", "" if venv.exists() else "run Launch Resume Taylor.bat once")

    missing = []
    for mod in ("fastapi", "uvicorn", "docx", "yaml", "pypdf", "multipart", "dotenv"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    line(not missing, "Python packages", ", ".join(missing) and f"missing: {', '.join(missing)}")
    problems += bool(missing)

    dist = ROOT / "frontend" / "dist" / "index.html"
    line(dist.exists(), "Web app files (frontend/dist)")
    problems += not dist.exists()

    claude = shutil.which("claude") or shutil.which("claude", path=str(Path.home() / ".local" / "bin"))
    line(bool(claude), "Claude tool installed", claude or "run Launch Resume Taylor.bat to install it")
    problems += not claude
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    try:
        from dotenv import dotenv_values

        env_key = env_key or (dotenv_values(ROOT / ".env").get("ANTHROPIC_API_KEY") or "")
    except ImportError:
        pass

    from resume_taylor.app.storage.paths import default_data_root

    data_root = default_data_root()
    saved_key = (data_root / "secrets.json").exists()
    if claude:
        raw = run([claude, "auth", "status"])
        try:
            logged_in = bool(json.loads(raw).get("loggedIn"))
        except ValueError:
            logged_in = None
        if logged_in:
            line(True, "Signed in to Claude")
        elif env_key.strip() or saved_key:
            line(True, "Anthropic API key found", "used instead of a Claude sign-in")
        else:
            line(False if logged_in is False else None, "Signed in to Claude",
                 "run:  claude auth login   (or paste an API key in the app's Settings)")
            problems += logged_in is False

    word = False
    if sys.platform == "win32":
        try:
            import winreg

            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"))
            word = True
        except OSError:
            pass
    line(word, "Microsoft Word (only needed for PDF)", "" if word else "without it you still get .docx files")

    line(data_root.exists(), "Your data folder", str(data_root))

    port_taken = False
    with socket.socket() as s:
        port_taken = s.connect_ex(("127.0.0.1", 8765)) == 0
    line(None, "Port 8765", "in use (another Resume Taylor may be running; that is fine)" if port_taken else "free")

    print("\n" + ("Everything needed is in place." if not problems else f"{problems} thing(s) need attention (see [FAIL] above)."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
