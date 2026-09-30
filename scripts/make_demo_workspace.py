"""
Build a self-contained demo workspace (default: ./demo_workspace) around the
fictional persona in examples/demo_data.py: profile, base resume, fact bank,
never-claim list, and three projects at different stages. Two come with a
hand-written (truthful to the persona) result rendered through the real
pipeline, so the app looks lived-in without any Claude calls.

    python scripts/make_demo_workspace.py
    python launcher.py --data-root demo_workspace
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))

from taylor.demo import seed_workspace  # noqa: E402
from taylor.paths import Paths, remove_tree  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", type=Path, default=ROOT / "demo_workspace")
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
