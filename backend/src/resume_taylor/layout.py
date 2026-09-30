"""Where the repository's folders are. Standard library only, so the launcher can
use it before the Python packages are installed."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
BACKEND_SRC = PACKAGE_DIR.parent  # put on PYTHONPATH for the pipeline subprocess
REPO_ROOT = PACKAGE_DIR.parents[2]  # this package runs from a checkout (editable install)

FRONTEND_DIR = REPO_ROOT / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"  # the prebuilt web app (committed)

# The tailoring rules/methodology live in agent-native Claude Code skills
# (.claude/skills/*/SKILL.md) rather than in Python strings, so there's one source of
# truth shared by this pipeline and any interactive `/resume-tailoring` use.
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
