"""
Build a self-contained demo workspace (default: ./demo_workspace) around the
fictional persona in resume_taylor/sample_data/demo_data.py: profile, base resume, fact bank,
never-claim list, and three projects at different stages. Two come with a
hand-written (truthful to the persona) result rendered through the real
pipeline, so the app looks lived-in without any Claude calls.

    python scripts/make_demo_workspace.py
    python launcher.py --data-root demo_workspace
"""

import argparse
import sys
from pathlib import Path

from resume_taylor.app.services.demo import seed_workspace
from resume_taylor.app.storage.fs import remove_tree
from resume_taylor.app.storage.paths import Paths
from resume_taylor.layout import REPO_ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "demo_workspace")
    parser.add_argument("--force", action="store_true", help="replace an existing demo workspace")
    args = parser.parse_args()

    target = args.out.resolve()
    if target.exists():
        if not args.force:
            sys.exit(f"{target} exists. Re-run with --force to rebuild it.")
        remove_tree(target)
    paths = Paths(target)
    paths.ensure()

    seed_workspace(paths)
    print(f"Demo workspace ready at {target}\nRun: python launcher.py --data-root {target.name}")


if __name__ == "__main__":
    main()
