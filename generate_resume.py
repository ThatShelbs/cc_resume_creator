"""Shim so `python generate_resume.py` keeps working. The code lives in `resume_taylor.pipeline.cli`
(also: `python -m resume_taylor.pipeline`, or the matching console script after `pip install -e backend`)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend" / "src"))

from resume_taylor.pipeline.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
