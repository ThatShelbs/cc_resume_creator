"""
Draft resume_input/fact_bank.yaml from the profile and prior resume.

The fact bank is the tailoring pipeline's source of truth: one atomic, true
fact per entry, each tagged with the employer it belongs to. generate_resume.py
requires every output bullet to cite fact ids from it, so no bullet can exist
without a traceable source. This script only DRAFTS the bank with one Claude
Code CLI call; review it by hand afterward (especially any `employer:
unassigned` entries), then keep it as a hand-maintained file.

Usage:
    python build_fact_bank.py          # refuses to overwrite an existing bank
    python build_fact_bank.py --force  # redraft from scratch (loses hand edits)
    python build_fact_bank.py --profile P --resume R --out PATH
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

import generate_resume as g

FACT_BANK_PATH = g.FACT_BANK_PATH

EXTRACT_SYSTEM_PROMPT = """You are a careful data-extraction tool. You convert a \
candidate's career documents into a list of atomic facts. You never add, infer, \
embellish, or merge information; you only restructure what is written.

Rules:
- One fact per distinct accomplishment, responsibility, skill, trait, award, or \
project detail. Split compound bullets only when they contain separate claims.
- "text": restate the fact as close to the source wording as possible. Keep every \
qualifier ("in progress", "expecting to", "helped", "partnered with") exactly; never \
upgrade "expecting to save" into "saved" or "helped" into "led".
- "employer": the exact employer name from the EMPLOYERS list when the source \
explicitly ties the fact to that employer (it names the company, or it appears under \
that employer in the prior resume). Use "general" for skills, tools, traits, and \
leadership statements that describe the candidate overall. Use "unassigned" when a \
fact is clearly job-specific but the source does not say which employer; never guess.
- "kind": one of accomplishment, responsibility, project, skill, tool, trait, award.
- "metrics": every number in the fact, copied exactly as written in the source \
(e.g. "$300k", "200+ hours", "50+"). Empty list if none.
- "tags": 2-6 short lowercase topic tags (e.g. "marketing mix modeling", \
"team leadership", "generative ai", "causal inference").
- Cover every bullet and skill line in both documents. Skip contact info and hobbies.

Return only a JSON array of objects with exactly the keys text, employer, kind, \
metrics, tags, wrapped in <FACTS> and </FACTS> tags, with nothing else in your reply."""


def _number_digits(s: str) -> str:
    return re.sub(r"[^\d]", "", s)


def draft_facts(profile_text: str, resume_text: str, companies: list) -> list:
    claude_bin = g._find_claude_cli()
    user_message = f"""EMPLOYERS (use these exact names):
{chr(10).join(companies)}

PROFILE:
{profile_text}

PRIOR RESUME:
{resume_text}"""
    for attempt in range(3):
        raw = g._invoke_claude(claude_bin, EXTRACT_SYSTEM_PROMPT, user_message)
        match = re.search(r"<FACTS>(.*?)</FACTS>", raw, re.DOTALL)
        try:
            facts = json.loads(g._strip_code_fence(match.group(1) if match else raw))
        except json.JSONDecodeError:
            facts = None
        if isinstance(facts, list) and facts:
            return facts
        print(f"  Attempt {attempt + 1} did not return a usable fact list, retrying...")
    sys.exit(f"Could not extract facts after 3 attempts. Last raw response:\n{raw}")


def normalize_facts(facts: list, companies: list, source_text: str) -> list:
    """Deterministic cleanup: assign stable ids ourselves, snap employer names to
    the parsed list, and demote any metric that isn't literally in the source."""
    source_digits = {_number_digits(n) for n in g.NUMBER_RE.findall(source_text)}
    cleaned = []
    for fact in facts:
        text = str(fact.get("text", "")).strip()
        if not text:
            continue
        employer = g.snap_employer(fact.get("employer", "unassigned"), companies) or "unassigned"
        metrics = []
        for m in fact.get("metrics") or []:
            m = str(m).strip()
            if _number_digits(m) and _number_digits(m) not in source_digits:
                print(f"  Dropped metric {m!r} (not found in source) from: {text[:70]}")
                continue
            metrics.append(m)
        cleaned.append(
            {
                "id": f"F{len(cleaned) + 1:03d}",
                "employer": employer,
                "kind": str(fact.get("kind", "accomplishment")).strip().lower(),
                "text": g.remove_em_dashes(text),
                "metrics": metrics,
                "tags": [str(t).strip().lower() for t in fact.get("tags") or [] if str(t).strip()],
            }
        )
    return cleaned


HEADER = """\
# Fact bank: the source of truth for tailoring. Every resume bullet must cite
# the ids of the facts it is built from, and generate_resume.py rejects a bullet
# that cites an unknown id or another employer's fact.
#
# Drafted by build_fact_bank.py, then maintained BY HAND:
#   - Fix every `employer: unassigned` entry (set the real employer, or `general`).
#     Unassigned facts can still inform the summary but never an employer's bullets.
#   - Correct any text that drifted from what you actually did.
#   - Add new accomplishments here as they happen; give each a new unique id.
# Keep ids stable once a resume has been generated, since briefs reference them.

"""


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Draft the fact bank from the profile and prior resume.")
    parser.add_argument("--force", action="store_true", help="overwrite an existing bank (loses hand edits)")
    parser.add_argument("--profile", type=Path, help="profile .docx (default: newest resume_input/in_profile*)")
    parser.add_argument("--resume", type=Path, help="prior resume .docx (default: newest resume_input/in_resume*)")
    parser.add_argument("--out", type=Path, default=FACT_BANK_PATH, help="where to write the bank")
    args = parser.parse_args(argv)
    out_path = args.out

    if out_path.exists() and not args.force:
        sys.exit(
            f"{g._display(out_path)} already exists and may contain hand edits. "
            "Edit it directly, or re-run with --force to redraft it from scratch."
        )

    profile_path = args.profile or g.find_latest("in_profile")
    resume_path = args.resume or g.find_latest("in_resume")
    companies = [job["company"] for job in g.parse_prior_resume(resume_path)["jobs"]]
    profile_text = g.read_docx_text(profile_path)
    resume_text = g.read_docx_text(resume_path)

    g.stage("drafting")
    print(f"Extracting facts from {profile_path.name} and {resume_path.name}...")
    facts = normalize_facts(
        draft_facts(profile_text, resume_text, companies),
        companies,
        profile_text + "\n" + resume_text,
    )

    g.stage("validating")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        HEADER + yaml.safe_dump({"facts": facts}, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    unassigned = sum(1 for f in facts if f["employer"] == "unassigned")
    print(f"Wrote {len(facts)} facts to {g._display(out_path)}.")
    if unassigned:
        print(f"  {unassigned} fact(s) are `employer: unassigned`; review and fix them by hand.")
    g.stage("done")


if __name__ == "__main__":
    main()
