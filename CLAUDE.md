# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

This tool is intended to be an agent that can automate the resume tailoring for a given job. 

Core rules for the project:

- Do not stretch the truth or put the applicant over their skis for interviews. Only use accomplishments, metrics, and skills that actually appear in the input files.
- Create a new resume adapted from the input files, optimized for getting interview and screening calls for the specific role in the input folder.
- Avoid heavy use of em dashes in generated text. It reads as an obvious AI-writing artifact. Prefer a period, comma, semicolon, or parentheses instead.

The **full, authoritative tailoring rules** (truthfulness, tailoring strategy, natural-terminology / anti-buzzword, summary, skills, writing style, evidence-based practices, output discipline) live in the `resume-tailoring` skill at `.claude/skills/resume-tailoring/SKILL.md`. That skill is the single source of truth: `generate_resume.py` loads its body verbatim as the tailoring system prompt, and it is also invokable interactively as `/resume-tailoring`. When you need to change how tailoring behaves, edit the skill, not a prompt string in the Python.

The intended workflow: read all files from `resume_input/`, generate a tailored resume into `resume_create/`, and move superseded versions into `resume_archive/`.

## Repository layout

- `resume_input/` — source; this folder will contain pdf, docx, and other files that are meant to help with creating a new resume. 
	- `in_profile` files will contain the contact info, experience, skills, projects, and acomplishments to pull from. 
	- `in_resume` is an example resume the user has used in the past.
	- `in_job` is the posting for the current role we want to design a new resume for. 


- `resume_create/` — when we create a new output resume we save it as `out_resume_fname-lname_yyyy-mm-dd`. We should make a copy as word .docx and a second copy as pdf in create folder.
- `resume_archive/` — when we create a new output resume we save the existing one here `out_resume_fname-lname_yyyy-mm-dd-hh-mm-ss` we will only save the .docx versions.
- `LICENSE` — MIT, copyright Shelby Temple.
- `generate_resume.py` — the orchestration script (deterministic parsing, LLM call, validation guards, docx/pdf output). It contains no tailoring rules of its own; it loads them from the skill below.
- `.claude/skills/resume-tailoring/SKILL.md` — the agent-native home for the tailoring methodology and rules. Single source of truth, used both by the pipeline and by an interactive `/resume-tailoring` invocation. See the "Skills" section below.
- `resume_best_practices.md` — evidence-based resume/ATS guidance researched once and cached, so the generator doesn't re-research it (or spend tokens/time on it) on every run. Only claims traceable to a named study or a company's own reported data are included. Referenced by the resume-tailoring skill.

## Skills

- **`resume-tailoring`** (`.claude/skills/resume-tailoring/SKILL.md`) — encodes how to tailor a candidate's real history to one job posting without fabrication: truthfulness rules, tailoring strategy, natural-terminology / anti-buzzword guidance, summary and skills rules, writing style, evidence-based practices, and output discipline. This is the agent-centric core of the project. `generate_resume.py` strips the YAML frontmatter and uses the body verbatim as the system prompt for its tailoring call, so editing the skill changes how generation behaves with no code change. It is also directly invokable (`/resume-tailoring`) when tailoring or reviewing a resume interactively.

When adding or changing tailoring behavior, prefer editing this skill (or adding a new skill under `.claude/skills/`) over hardcoding logic in Python. Keep genuinely deterministic concerns (parsing source docs, sorting/dedup, format enforcement, docx layout) in `generate_resume.py`, and keep judgment/writing rules in the skill.

## Running the generator

```
pip install -r requirements.txt
claude /login   # one-time, if not already logged in
python generate_resume.py
```

No API key is required — the script shells out to the Claude Code CLI (`claude -p`), which authenticates with your logged-in Claude subscription instead of billing per token.

Contact info, education, and each employer's company/location/dates/title are parsed deterministically out of `resume_input/in_profile*` and `in_resume*` with plain Python (no LLM involved) — there's no tailoring judgment in those fields, so doing it in code is faster, cheaper, and can't introduce a transcription error. The CLI is only asked to produce the parts that actually require judgment: a tailored summary, per-employer bullets selected from true source material, and a tailored skills list, following the `resume-tailoring` skill's rules. The call sequence is: a free-form tailoring draft, then a narrow reformatting call that transcribes the draft's summary and bullets into JSON. The skills list is not taken from that JSON (the model unreliably flattens categorized skill groupings); instead it is extracted deterministically from the draft's competencies section. Each CLI call runs with `--tools ""` (pure text generation, no file/tool access), a scrubbed subprocess environment (CLAUDE_*/ANTHROPIC_* stripped), and `cwd` set outside this repo — without those, the call picks up this repo's own `CLAUDE.md` and starts behaving like an interactive coding assistant instead of a one-shot text transform.

The tailoring rules come from the `resume-tailoring` skill and are passed with `--system-prompt-file` (a temp file), **not** `--system-prompt`: on Windows the `claude` entry is a `.CMD` shim run through `cmd.exe`, which caps the whole command line at 8191 characters, so a long inline system prompt overflows it ("The command line is too long."). Routing the prompt through a file removes that limit. Do not switch back to passing the system prompt as an inline argument.

After generation, several deterministic Python checks run against the source documents before anything is written: bullets that mention a different employer are dropped, an inflated total-years-of-experience claim is corrected to match the prior resume, any lingering em dash is replaced with a comma, and bullets with unsupported numbers, unverified skills, or job-posting-buzzword "analogous to X" phrasing are flagged as console warnings for manual review (not silently modified — the model's judgment calls that don't cleanly map to a deterministic check still need a human read before sending). Skill labels pulled from the draft pass through a filter that rejects sentence-like entries, duration/scope qualifiers, and sentence fragments (keeping short canonical labels); the profile's Software/Tools and Skills entries that the job posting also names are force-included as a backfill; then the merged list is deduplicated and sorted alphabetically.

It then archives whatever is currently in `resume_create/` before writing the new `.docx`/`.pdf`. PDF generation uses `docx2pdf`, which drives MS Word via COM automation and therefore only works on Windows with Word installed — the `.docx` is still produced if that step fails.

