"""
Resume Studio: a local browser front end for the resume pipeline.

The studio never tailors anything itself. It keeps the pipeline's canonical
inputs (resume_input/in_profile*.docx, in_resume*.docx, fact_bank.yaml,
do_not_claim.txt) in the exact layout generate_resume.py parses, stores one
folder per job application under projects/, and runs generate_resume.py as a
subprocess for every generation or re-render. The tailoring rules still live
only in .claude/skills/.
"""

import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

__version__ = "1.0.0"
