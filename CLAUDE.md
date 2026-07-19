# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

This tool is intended to be an agent that can automate the resume tailoring for a given job. 

Here are the rules for the project:

- Do not stretch the truth or put the applicant over their skiis for interviews
- Create a new resume adapted from input files to generate a new resume optimized for getting interview and screening calls for the specific role also in the input folder
- Avoid heavy use of em dashes in generated text. It reads as an obvious AI-writing artifact. Prefer a period, comma, semicolon, or parentheses instead.

The intended workflow — read all files from `resume_input/`, generate a tailored resume into `resume_create/`, and move superseded versions into `resume_archive/` 

## Repository layout

- `resume_input/` — source; this folder will contain pdf, docx, and other files that are meant to help with creating a new resume. 
	- `in_profile` files will contain the contact info, experience, skills, projects, and acomplishments to pull from. 
	- `in_resume` is an example resume the user has used in the past.
	- `in_job` is the posting for the current role we want to design a new resume for. 


- `resume_create/` — when we create a new output resume we save it as `out_resume_fname-lname_yyyy-mm-dd`. We should make a copy as word .docx and a second copy as pdf in create folder.
- `resume_archive/` — when we create a new output resume we save the existing one here `out_resume_fname-lname_yyyy-mm-dd-hh-mm-ss` we will only save the .docx versions.
- `LICENSE` — MIT, copyright Shelby Temple.
- `generate_resume.py` — the script that implements the workflow above.
- `resume_best_practices.md` — evidence-based resume/ATS guidance researched once and cached, so the generator doesn't re-research it (or spend tokens/time on it) on every run. Only claims traceable to a named study or a company's own reported data are included.

## Running the generator

```
pip install -r requirements.txt
claude /login   # one-time, if not already logged in
python generate_resume.py
```

No API key is required — the script shells out to the Claude Code CLI (`claude -p`), which authenticates with your logged-in Claude subscription instead of billing per token.

Contact info, education, and each employer's company/location/dates/title are parsed deterministically out of `resume_input/in_profile*` and `in_resume*` with plain Python (no LLM involved) — there's no tailoring judgment in those fields, so doing it in code is faster, cheaper, and can't introduce a transcription error. The CLI is only asked to produce the parts that actually require judgment: a tailored summary, per-employer bullets selected from true source material, and a tailored skills list, drawing on `resume_best_practices.md`'s condensed checklist. That two-call sequence (free-form draft, then a narrow reformatting call) runs with `--tools ""` (pure text generation, no file/tool access), a scrubbed subprocess environment, and `cwd` set outside this repo — without those, the CLI call picks up this repo's own `CLAUDE.md` and starts behaving like an interactive coding assistant instead of a one-shot text transform. (An earlier version tried to skip the second call by parsing the free-form draft directly with regex; that silently leaked section headers and markdown dividers into the summary field, so it was removed in favor of always going through the structured JSON call.)

After generation, several deterministic Python checks run against the source documents before anything is written: bullets that mention a different employer are dropped, an inflated total-years-of-experience claim is corrected to match the prior resume, any lingering em dash is replaced with a comma, and bullets with unsupported numbers, unverified skills, or job-posting-buzzword "analogous to X" phrasing are flagged as console warnings for manual review (not silently modified — the model's judgment calls that don't cleanly map to a deterministic check still need a human read before sending). The skills list is also backfilled: any skill/tool listed in the profile's Software/Tools or Skills sections that's also explicitly named in the job posting is force-included even if the model's draft omitted it, then the merged list is deduplicated and sorted alphabetically.

It then archives whatever is currently in `resume_create/` before writing the new `.docx`/`.pdf`. PDF generation uses `docx2pdf`, which drives MS Word via COM automation and therefore only works on Windows with Word installed — the `.docx` is still produced if that step fails.

