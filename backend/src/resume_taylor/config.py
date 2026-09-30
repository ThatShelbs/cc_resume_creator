"""Settings read from the environment, and the command-line pipeline's default files.

Folder locations of the repository itself live in `layout`; this module adds what
depends on the environment (.env) and the pipeline's own data folders.
"""

import os

from dotenv import load_dotenv

from .layout import PACKAGE_DIR, REPO_ROOT, SKILLS_DIR

# The command-line pipeline's own folders (git-ignored personal data). The app keeps
# its data outside the repo instead; see resume_taylor.app.storage.paths.
INPUT_DIR = REPO_ROOT / "resume_input"
CREATE_DIR = REPO_ROOT / "resume_create"
ARCHIVE_DIR = REPO_ROOT / "resume_archive"

# Load .env before reading any setting from the environment (build_fact_bank
# imports this module, so it picks these up too).
load_dotenv(REPO_ROOT / ".env")

MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")
EFFORT = os.environ.get("CLAUDE_EFFORT", "medium")
CLAUDE_TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT", "600"))  # seconds per CLI call

TAILORING_SKILL_PATH = SKILLS_DIR / "resume-tailoring" / "SKILL.md"
COVER_LETTER_SKILL_PATH = SKILLS_DIR / "cover-letter" / "SKILL.md"

# Hard "never claim" list (claim tier T4 in the skill): one regex per line.
DO_NOT_CLAIM_PATH = REPO_ROOT / "do_not_claim.txt"
DO_NOT_CLAIM_EXAMPLE = PACKAGE_DIR / "resources" / "do_not_claim.example.txt"  # tracked starter list

# Hand-maintained bank of atomic, employer-tagged facts (drafted by
# build_fact_bank). When present, every bullet must cite fact ids from it.
FACT_BANK_PATH = INPUT_DIR / "fact_bank.yaml"
