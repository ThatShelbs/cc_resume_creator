"""Subprocess helpers shared by the app: hide console windows on Windows, and run the
pipeline from this checkout with the backend importable."""

import os
import sys

from .layout import BACKEND_SRC

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW


def with_backend_on_path(env: dict) -> dict:
    """`env` plus PYTHONPATH pointing at backend/src, so `python -m resume_taylor...`
    works in a child process even when the package isn't installed."""
    existing = env.get("PYTHONPATH")
    return {**env, "PYTHONPATH": os.pathsep.join([str(BACKEND_SRC), existing] if existing else [str(BACKEND_SRC)])}
