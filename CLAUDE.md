# CLAUDE.md

Guidance for Claude Code when working in this repository. Setup, CLI flags and the architecture diagram are in [CONTRIBUTING.md](CONTRIBUTING.md); brand and naming rules are in `docs/brand/BRAND.md`.

## Project purpose

An agent that tailors a resume to one job posting. Core rules:

- Do not stretch the truth or put the applicant over their skis for interviews. Only use accomplishments, metrics, and skills that actually appear in the input files.
- Create a new resume adapted from the input files, optimized for interview and screening calls for the specific role.
- Avoid heavy use of em dashes in generated text (and UI copy). It reads as an obvious AI-writing artifact. Prefer a period, comma, semicolon, or parentheses.

The **authoritative tailoring rules** live in the `resume-tailoring` skill (`.claude/skills/resume-tailoring/SKILL.md`). `generate_resume.py` loads its body verbatim (frontmatter stripped by `load_skill()`) as the tailoring system prompt, and it is invokable as `/resume-tailoring`. To change tailoring behavior, edit the skill (or add one under `.claude/skills/`), never a prompt string in Python. Keep deterministic concerns (parsing, sorting/dedup, format enforcement, docx layout) in `generate_resume.py`, judgment and writing rules in the skills, and app plumbing in `taylor/`.

## Repository layout

- `generate_resume.py`: the pipeline (deterministic parsing, Claude calls, validation guards, docx/pdf output). No tailoring rules of its own.
- `build_fact_bank.py`: drafts `fact_bank.yaml` once with one `claude -p` call (ids and metric checks assigned in Python; refuses to overwrite without `--force`).
- `taylor/`: Resume Taylor's FastAPI backend. `webapp/frontend/`: its React app (Vite, TypeScript, Tailwind, Radix/shadcn-style components); `npm run build` writes `dist/`, which the backend serves.
- `launcher.py`, `Launch Resume Taylor.bat`: start the app. The .bat is the installer for non-technical users (Python via winget, `.venv`, requirements, `.env` from `.env.example`, Claude CLI, `claude auth login`). Helpers: `Doctor.bat` (`scripts/doctor.py`), `Update.bat`, `Create Desktop Shortcut.bat`.
- `.claude/skills/`: `resume-tailoring` and `cover-letter` (rules for `--cover-letter`, loaded the same way).
- `resume_best_practices.md`: cached, sourced resume/ATS guidance referenced by the skill, so it is not re-researched each run.
- `examples/`: `make_examples.py` builds anonymized sample inputs in the layout the parser expects; `demo_data.py` is the fictional Jordan Rivera applicant. `tests/`: pytest suite for the deterministic code, no LLM calls.
- `scripts/`: `make_demo_workspace.py`, `make_template_previews.py` (needs Word), `capture_screenshots.py` and `make_brand_assets.py` (need Playwright), `export_openapi.py` (for `npm run gen:api`), `check_no_personal_data.py`, `doctor.py`, `create_desktop_shortcut.ps1`.
- `docs/`: `brand/` (BRAND.md, `banner.html` and rendered PNGs) and README `screenshots/`.
- `do_not_claim.example.txt` (tracked starter) / `do_not_claim.txt` (git-ignored; the generator falls back to the example): the hard "never claim" list (tier T4 in the skill), one case-insensitive regex per line. Any match in the generated summary, bullets, or skills aborts the run before anything is archived or written. Use phrases, not bare words.

### CLI data folders

`resume_input/`, `resume_create/`, `resume_archive/` are git-ignored (only `.gitkeep` tracked): they hold personal career data and must never be committed. The CLI uses them; the app's data folder is outside the repo.

- `resume_input/`: `in_profile*` (contact info, experience, skills, accomplishments), `in_resume*` (a prior resume), `in_job*` (the posting), optional `fact_bank.yaml`.
- `resume_create/`: `out_resume_fname-lname_yyyy-mm-dd` as `.docx` and `.pdf`, plus `_report.md` (inputs, every warning, keyword coverage, each bullet with its cited facts, raw draft). `--cover-letter` adds `out_cover_letter_...docx/.pdf`.
- `resume_archive/`: whatever was in `resume_create/` is moved here with a `-hh-mm-ss` suffix before new files are written (`.docx` and matching `_report.md` only).

### Resume Taylor data and secrets

- Personal data lives outside the repo: `taylor/paths.py:default_data_root()` is `%LOCALAPPDATA%\ResumeTaylor` (override with `RESUME_TAYLOR_DATA` or `--data-root`). `projects/` holds one folder per application (git-ignored).
- `webapp/frontend/dist` IS committed (prebuilt, so users need no Node). Rebuild and commit it after any frontend change; CI checks. `scripts/check_no_personal_data.py` (pre-commit hook via `--install-hook`, and CI) blocks resumes, keys and project folders.
- API key is optional: `taylor/credentials.py` stores it in `<data root>/secrets.json` (never returned by the API, redacted in logs); `taylor/api.py:job_env()` passes it to the pipeline as `ANTHROPIC_API_KEY`, and `generate_resume._clean_subprocess_env()` keeps only that one ANTHROPIC var. Precedence: app key, then `.env`, then the CLI login.
- Sample data: `taylor/demo.py` seeds Jordan Rivera via `POST /api/demo/load` (only into a folder with no profile/resume); a `.sample_data.json` marker lets `POST /api/demo/clear` remove exactly that, backing up first if edited.

## Running the generator

```
pip install -r requirements.txt
claude /login   # one-time
python generate_resume.py   # flags: see CONTRIBUTING.md
python launcher.py          # Resume Taylor in the browser
```

No API key is required: the script shells out to the Claude Code CLI (`claude -p`), which uses the logged-in subscription.

The posting may be `.docx`, `.pdf` (`pypdf`), `.txt`, or `.md` (`read_input_text()`); the profile and prior resume must stay `.docx` because their structure is parsed. The page count is checked after PDF export (warning over 2 pages). The email and any LinkedIn URL in the contact line are real hyperlinks. `.env` is loaded at import time of `generate_resume.py` (before `CLAUDE_MODEL`/`CLAUDE_EFFORT`/`CLAUDE_TIMEOUT` are read), so it also applies to `build_fact_bank.py`. `find_latest()` picks the newest `in_*` file by mtime. Advisory warnings go through `warn()`, which prints and collects into `WARNINGS` for the report; route any new warning through it.

**Pipeline.** Contact info, education, and each employer's company/location/dates/title are parsed in plain Python (no transcription errors). Claude only produces what needs judgment: a tailored summary, per-employer bullets from true source material, and a skills list. The sequence is a free-form tailoring draft, then a narrow reformatting call that transcribes the draft's summary and bullets to JSON. Skills are not taken from that JSON (the model flattens categories unreliably); they are extracted deterministically from the draft's competencies section, filtered to short canonical labels, backfilled with profile tools/skills the posting names, deduplicated and sorted. Each CLI call runs with `--tools ""`, a scrubbed environment (CLAUDE_*/ANTHROPIC_* stripped), and `cwd` outside this repo; otherwise it picks up this CLAUDE.md and behaves like a coding assistant instead of a text transform.

The system prompt is passed with `--system-prompt-file` (a temp file), **not** `--system-prompt`: on Windows `claude` is a `.CMD` shim run through `cmd.exe`, which caps the command line at 8191 characters ("The command line is too long."). Do not switch back to an inline argument.

**Guards** run against the source documents before anything is written: bullets naming a different employer are dropped, an inflated total-years claim is corrected to match the prior resume, em dashes become commas, and unsupported numbers, unverified skills, or buzzword "analogous to X" phrasing are flagged as warnings (not silently modified; a human still reads them). With a fact bank the tailoring call must end every bullet with `[F###, ...]` citations; `validate_citations()` strips them and drops any bullet citing an unknown id, an `unassigned` fact, or another employer's fact, and warns on uncited bullets and numbers absent from the cited facts. Without a bank the run works minus provenance checks. `validate_cover_letter()` does the same for the letter (uncited closing paragraph allowed) and the never-claim list aborts just as for the resume.

`load_fact_bank()` snaps each fact's employer onto parsed employer names (`snap_employer()`, shared with `build_fact_bank.py`), warns on labels matching none, and treats those facts as `unassigned`. An employer left with no tailored bullets falls back to its prior-resume bullets, with a warning. `keyword_coverage()` reports which posting terms from the candidate's own vocabulary (profile tools/skills plus fact-bank tags) the output uses, so every "missing" term is a truthful gap, never a prompt to claim something new.

PDF generation uses `docx2pdf`, which drives Word via COM (Windows with Word only); the `.docx` is still produced if it fails.

## Resume Taylor (browser app)

A local web front end over the same pipeline. It never tailors anything itself.

- **Inputs stay canonical.** The profile editor writes `in_profile.docx` in the paragraph layout `parse_applicant_info()`/`parse_profile_skills()` read (`taylor/profile_store.py`). An uploaded resume (PDF or Word) is parsed deterministically (`taylor/resume_ingest.py`: structured docx first, then a heuristic text parser; a one-shot verbatim Claude extraction only when that finds no employers), every field is checked against the file's text and flagged if not found verbatim, and only after the user confirms is it written as a normalized `in_resume_<First-Last>.docx` that `parse_prior_resume()` reads exactly. The fact bank and never-claim list are edited in place (`taylor/facts.py`); every save backs the old file up to `resume_archive/`.
- **All generation and rendering runs `generate_resume.py` as a subprocess** (`taylor/jobs.py`, one job at a time on a worker thread) with `TAYLOR_PROGRESS=1`, so it prints `::stage <name>` and `::deny {json}` lines that the server streams to the UI over Server-Sent Events. This keeps module-level `WARNINGS`, `sys.exit()` handling, and Word COM out of the server process. A job's `status` becomes final only after its `on_success`/`on_finish` callbacks have installed the results, so a client that refetches on "succeeded" always sees the new files.
- **Pipeline flags used by the app:** `--profile/--resume/--job/--fact-bank/--deny`, `--out-dir` (per-job staging), `--template {classic,modern,compact}`, `--result-json` (structured, editable result: contact, summary, education, experience with `{text, ids}` bullets, skills, cover letter, coverage, warnings, draft), and `--render-json` (re-validate a possibly hand-edited result with the same guards, never dropping content except that a never-claim hit still aborts, then write files; no Claude call). Classic is byte-for-byte the original layout; templates are `TemplateSpec`s in `TEMPLATES`, single-column, nothing in headers/footers.
- **Project store** (`taylor/projects.py`): `projects/<id>/{project.json, job.txt, result.json, outputs/, versions/<ts>/, inputs_snapshot/, run.log}`. A generation installs from staging and keeps what it replaces in `versions/` (copy-first, so a failure never leaves a half-rotated project; PDFs aren't archived). Re-renders replace `outputs/` without a version. Deleting moves to `projects/_trash/`.
- **Windows paths:** `Paths` makes every data path extended-length (`\\?\`) so deep folders (e.g. under OneDrive) can't hit MAX_PATH; anything passed to Word or shown to the user goes through `plain_path()`. Use `remove_tree()` (clears OneDrive's read-only attribute, retries) instead of `shutil.rmtree`.
- **Live checks while editing** (`taylor/lint.py`) mirror the pipeline's guards per line for inline badges only; the render still runs the real guards.
- **Security:** binds to 127.0.0.1, rejects non-loopback `Host` headers, and requires the per-launch token (injected into `index.html`; `X-Taylor-Token` header or `?t=`) on every `/api` call except `/api/health` and the docs.
- **Tests:** `python -m pytest -q` (API tests swap in a fake pipeline script; no Claude calls) and `npm run check` in `webapp/frontend` (typecheck, ESLint, Vitest). After changing a Pydantic request model, run `npm run gen:api`.
