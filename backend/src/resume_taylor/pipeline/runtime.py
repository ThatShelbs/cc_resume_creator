"""Run-wide state shared by every pipeline module: the advisory-warning log and the
progress markers Resume Taylor (the browser app) follows."""

import os

# Every advisory warning raised during a run, collected for the report.
WARNINGS: list = []


def warn(msg: str) -> None:
    print(f"  Warning: {msg}")
    WARNINGS.append(msg)


# Resume Taylor (the browser app) runs this script as a subprocess and sets
# TAYLOR_PROGRESS=1 so it can follow along. The "::stage <name>" lines it then
# gets are a stable, machine-readable progress signal, so the app never has to
# parse the human-facing messages. Plain CLI runs don't print them.
PROGRESS_MARKERS = os.environ.get("TAYLOR_PROGRESS") == "1"


def stage(name: str) -> None:
    if PROGRESS_MARKERS:
        print(f"::stage {name}", flush=True)
