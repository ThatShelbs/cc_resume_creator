"""Stand-in for the `claude` CLI used by test_cli.py: canned, deterministic replies
keyed on the system prompt, shaped like `claude -p --output-format json`."""

import json
import os
import sys

args = sys.argv[1:]
system_prompt = ""
if "--system-prompt-file" in args:
    with open(args[args.index("--system-prompt-file") + 1], encoding="utf-8") as fh:
        system_prompt = fh.read()
sys.stdin.read()

DRAFT = """## Summary
Analytics leader with 15+ years of experience — turning data into decisions.

## Core Competencies
**Measurement:** Marketing Mix Modeling | A/B Testing | Forecasting
**Leadership:** Team Leadership | Stakeholder Management
**Tools:** Python | SQL | dbt | Snowflake | Rust
"""

RESUME_JSON = {
    "summary": "Analytics leader with 15+ years of experience — built a marketing mix model that reallocated $4M of annual spend.",
    "bullets_by_company": {
        "Northwind Traders": [
            "Launched a marketing mix model that reallocated $4M of annual spend toward higher-return channels. [F002]",
            "Designed an experimentation program running 40+ A/B tests per year — across web and email. [F003]",
            "Built a customer churn model that cut churn 12% in one year. [F001]",
            "Cut churn cost by $95M annually with the model. [F001]",
            "Built store-level demand forecasts that reduced stockouts 18%. [F006]",
            "Mentored analysts into lead roles.",
            "Lead a team of 7 analysts and data scientists, partnering with marketing, finance, and product leaders. [F004, F010]",
        ],
        "Contoso Retail": [
            "Built store-level demand forecasts that reduced stockouts 18%. [F006]",
            "Automated weekly sales reporting in SQL, saving 10 hours per week. [F005]",
        ],
        "Fabrikam Health": [
            "Built patient segmentation used by 3 regional outreach teams. [F007]",
            "Applied Northwind experimentation methods to health outreach. [F008]",
            "Created Tableau dashboards analogous to executive reporting. [F008]",
        ],
    },
    "skills": ["Ignored", "because", "the", "draft wins"],
}

LETTER = """<COVER_LETTER>
I am excited to apply for the Head of Marketing Analytics role. At Northwind Traders I launched a marketing mix model that reallocated $4M of annual spend — the kind of measurement work your team needs. [F002]

I also designed an experimentation program running 40+ A/B tests per year. [F003] I lead 7 analysts and would bring that leadership to Lumen. [F004]

Thank you for your time and consideration.
</COVER_LETTER>"""

if os.environ.get("FAKE_CLAUDE_MODE") == "prohibited":
    RESUME_JSON["summary"] = "Certified Six Sigma black belt leader."

if "text-to-JSON transcription tool" in system_prompt:
    reply = "<RESUME_JSON>" + json.dumps(RESUME_JSON) + "</RESUME_JSON>"
elif "COVER_LETTER" in system_prompt:
    reply = LETTER
else:
    reply = DRAFT

print(json.dumps({"result": reply, "is_error": False}))
