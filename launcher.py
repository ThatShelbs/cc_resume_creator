"""
Start Resume Studio and open it in your browser.

    python launcher.py                       # your real data (this folder)
    python launcher.py --data-root demo_workspace
    python launcher.py --dev                 # Vite hot reload + API (for development)

On Windows, double-click "Launch Resume Studio.bat" instead: it prepares a
private Python environment first, then runs this. The launcher builds the web
app when its sources changed, reuses an already-running instance for the same
data folder, and stops the server when you close its window (or press Ctrl+C).
"""

import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "webapp" / "frontend"
DIST = FRONTEND / "dist"
BUILD_STAMP = FRONTEND / ".build-hash"  # outside dist/, which each build empties
DEV_API_PORT = 8765  # vite.config.ts proxies /api here

BANNER = r"""
  ____                                  ____  _             _ _
 |  _ \ ___  ___ _   _ _ __ ___   ___  / ___|| |_ _   _  __| (_) ___
 | |_) / _ \/ __| | | | '_ ` _ \ / _ \ \___ \| __| | | |/ _` | |/ _ \
 |  _ <  __/\__ \ |_| | | | | | |  __/  ___) | |_| |_| | (_| | | (_) |
 |_| \_\___||___/\__,_|_| |_| |_|\___| |____/ \__|\__,_|\__,_|_|\___/
"""


def say(msg: str = "") -> None:
    print(msg, flush=True)


def fail(msg: str) -> None:
    say(f"\n  {msg}\n")
    sys.exit(1)


def check_python() -> None:
    if sys.version_info < (3, 10):
        fail(f"Resume Studio needs Python 3.10 or newer (this is {sys.version.split()[0]}). Get it from python.org/downloads.")
    missing = []
    for module in ("fastapi", "uvicorn", "docx", "yaml", "pypdf", "multipart"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        fail(
            f"Missing Python packages: {', '.join(missing)}.\n"
            f"  Run:  {Path(sys.executable).name} -m pip install -r requirements.txt\n"
            "  (or double-click 'Launch Resume Studio.bat', which does this for you)."
        )


# ---------------------------------------------------------------------------
# Frontend build
# ---------------------------------------------------------------------------


def _frontend_inputs() -> list[Path]:
    files = [FRONTEND / name for name in ("package.json", "package-lock.json", "index.html", "vite.config.ts",
                                          "tailwind.config.ts", "postcss.config.js", "tsconfig.app.json")]
    for folder in ("src", "public"):
        files += sorted(
            p for p in (FRONTEND / folder).rglob("*")
            if p.is_file() and "test" not in p.relative_to(FRONTEND).parts and ".test." not in p.name
        )
    return [f for f in files if f.exists()]


def frontend_hash() -> str:
    h = hashlib.sha256()
    for f in _frontend_inputs():
        h.update(str(f.relative_to(FRONTEND)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:20]


def npm() -> str | None:
    return shutil.which("npm.cmd" if sys.platform == "win32" else "npm") or shutil.which("npm")


def run_npm(*args: str) -> None:
    exe = npm()
    subprocess.run([exe, *args], cwd=str(FRONTEND), check=True)


def ensure_frontend(force: bool = False) -> None:
    current = frontend_hash()
    built = BUILD_STAMP.read_text().strip() if BUILD_STAMP.exists() else ""
    if not force and (DIST / "index.html").exists() and built == current:
        return
    if not npm():
        if (DIST / "index.html").exists():
            say("  Note: Node.js/npm not found, so the web app can't be rebuilt; using the existing build.")
            return
        fail("The web app needs to be built once, which requires Node.js (https://nodejs.org).\n"
             "  Node is also what the Claude Code CLI runs on, so install it, then launch again.")
    say("  Building the web app (first run, or after an update). This takes a minute...")
    try:
        lock = FRONTEND / "package-lock.json"
        stamp = FRONTEND / "node_modules" / ".lock-hash"
        lock_hash = hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else ""
        if not (FRONTEND / "node_modules").exists() or not stamp.exists() or stamp.read_text().strip() != lock_hash:
            try:
                run_npm("ci", "--no-audit", "--no-fund", "--loglevel=error")
            except subprocess.CalledProcessError:
                run_npm("install", "--no-audit", "--no-fund", "--loglevel=error")
            stamp.write_text(lock_hash)
        run_npm("run", "build", "--silent")
    except subprocess.CalledProcessError:
        fail("Building the web app failed; see the messages above.")
    BUILD_STAMP.write_text(current)
    say("  Web app built.")


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


def health(port: int, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as r:
            return json.loads(r.read()).get("app") == "resume-studio"
    except (OSError, ValueError):
        return False


def port_file(data_root: Path) -> Path:
    return data_root / ".studio_port"


def running_port(data_root: Path) -> int | None:
    try:
        port = int(json.loads(port_file(data_root).read_text())["port"])
    except (OSError, ValueError, KeyError):
        return None
    return port if health(port) else None


def free_port(start: int) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    fail(f"No free local port found between {start} and {start + 99}.")
    return start


def open_when_ready(port: int, url: str, open_browser: bool) -> None:
    for _ in range(150):
        if health(port, 0.5):
            break
        time.sleep(0.2)
    say(f"  Resume Studio is running at {url}")
    say("  Keep this window open while you use it. Close it (or press Ctrl+C) to stop.\n")
    if open_browser:
        webbrowser.open(url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Resume Studio and open it in your browser.")
    parser.add_argument("--data-root", type=Path, help="folder with resume_input/, projects/, ... (default: this folder)")
    parser.add_argument("--port", type=int, default=8765, help="first port to try (default 8765)")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    parser.add_argument("--rebuild", action="store_true", help="force a rebuild of the web app")
    parser.add_argument("--dev", action="store_true", help="development mode: Vite hot reload on :5173")
    args = parser.parse_args()

    say(BANNER)
    check_python()
    data_root = (args.data_root or ROOT).resolve()
    data_root.mkdir(parents=True, exist_ok=True)

    existing = running_port(data_root)
    if existing and not args.dev:
        url = f"http://127.0.0.1:{existing}/"
        say(f"  Resume Studio is already running at {url}; opening it.")
        if not args.no_browser:
            webbrowser.open(url)
        return

    vite = None
    if args.dev:
        if not npm():
            fail("Dev mode needs Node.js/npm.")
        if not (FRONTEND / "node_modules").exists():
            run_npm("install")
        port, token = DEV_API_PORT, "dev"
        vite = subprocess.Popen([npm(), "run", "dev"], cwd=str(FRONTEND), env={**os.environ, "VITE_STUDIO_TOKEN": token})
        url = "http://localhost:5173/"
    else:
        ensure_frontend(force=args.rebuild)
        port, token = free_port(args.port), secrets.token_urlsafe(24)
        url = f"http://127.0.0.1:{port}/"

    import uvicorn

    from studio.api import create_app
    from studio.paths import Paths

    app = create_app(Paths(data_root), token)
    port_file(data_root).write_text(json.dumps({"port": port, "pid": os.getpid()}))
    threading.Thread(target=open_when_ready, args=(port, url, not args.no_browser), daemon=True).start()
    say(f"  Data folder: {data_root}")
    try:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            port_file(data_root).unlink()
        except OSError:
            pass
        if vite:
            vite.terminate()
        say("  Resume Studio stopped.")


if __name__ == "__main__":
    main()
