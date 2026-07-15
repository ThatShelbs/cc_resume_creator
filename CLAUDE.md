# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

This tool is intended to be an agent that can automate the resume tailoring for a given job. 

Here are the rules for the project:

- Do not stretch the truth or put the applicant over their skiis for interviews
- Create a new resume adapted from input files to generate a new resume optimized for getting interview and screening calls for the specific role also in the input folder

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

## Running the generator

```
pip install -r requirements.txt
claude /login   # one-time, if not already logged in
python generate_resume.py
```

No API key is required — the script shells out to the Claude Code CLI (`claude -p`), which authenticates with your logged-in Claude subscription instead of billing per token. It picks the latest-named `in_profile*`, `in_resume*`, and `in_job*` files from `resume_input/`, runs the CLI with tool access disabled (`--tools ""`) so it's a pure text-generation call, and asks it to return a single JSON object matching a fixed resume shape (model set via `CLAUDE_MODEL`, defaults to the `sonnet` alias). It then archives whatever is currently in `resume_create/` before writing the new `.docx`/`.pdf`. PDF generation uses `docx2pdf`, which drives MS Word via COM automation and therefore only works on Windows with Word installed — the `.docx` is still produced if that step fails.

