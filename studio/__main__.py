"""Run the Resume Studio server: `python -m studio --port 8765 --token ...`.
Normally started by launcher.py, which also picks the port, builds the
frontend when needed, and opens the browser."""

import argparse
import os
import secrets
from pathlib import Path

import uvicorn

from .api import create_app
from .paths import Paths, default_paths


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Resume Studio server")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", default=os.environ.get("STUDIO_TOKEN") or secrets.token_urlsafe(24))
    parser.add_argument("--data-root", help="folder holding resume_input/, projects/, ... (default: ResumeStudio in your local app data folder)")
    args = parser.parse_args(argv)

    paths = Paths(Path(args.data_root).resolve()) if args.data_root else default_paths()
    app = create_app(paths, args.token)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
