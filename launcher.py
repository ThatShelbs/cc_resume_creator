"""Shim so `python launcher.py` keeps working. The code lives in `resume_taylor.launcher`
(also: `python -m resume_taylor.launcher`, or the matching console script after `pip install -e backend`)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend" / "src"))

from resume_taylor.launcher import main  # noqa: E402

if __name__ == "__main__":
    main()
