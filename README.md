# cc_resume_creator

Generates a resume tailored to a specific job posting from your existing career
materials. It pulls your contact info, career history, and accomplishments from
`resume_input/`, tailors a summary/bullets/skills to the job posting using Claude,
and writes a formatted `.docx` + `.pdf` to `resume_create/` — without stretching the
truth. See [CLAUDE.md](CLAUDE.md) for how it works internally.

## Prerequisites

- **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads/)
- **The Claude Code CLI, installed and logged in** — this is what actually generates
  the tailored content, using your Claude subscription (no separate API key or
  billing needed):
  ```
  npm install -g @anthropic-ai/claude-code
  claude /login
  ```
  (requires [Node.js](https://nodejs.org/) for `npm`)
- **Microsoft Word, on Windows** — only needed for the `.pdf` output. The `.docx` is
  generated regardless; PDF export drives Word via COM automation, which only works
  on Windows with Word installed. If you're on WSL or don't have Word, you'll still
  get a `.docx` and a warning instead of a `.pdf`.

## 1. Get the code

```
git clone https://github.com/ThatShelbs/cc_resume_creator.git
cd cc_resume_creator
```

## 2. Install Python dependencies

**Command Prompt (cmd.exe)**
```cmd
cd path\to\cc_resume_creator
pip install -r requirements.txt
```

**PowerShell**
```powershell
cd path\to\cc_resume_creator
pip install -r requirements.txt
```

**WSL / bash**
```bash
cd /mnt/c/path/to/cc_resume_creator
pip3 install -r requirements.txt
```
> PDF export won't work from WSL (no access to Windows' Word installation) — the
> `.docx` will still be generated. Run from CMD or PowerShell if you need the PDF.

## 3. Add your input files

Drop these into `resume_input/` (see [CLAUDE.md](CLAUDE.md) for the exact naming/content
expectations):

- `in_profile*.docx` — your contact info, full career details, skills, projects
- `in_resume*.docx` — a prior resume (defines your official job titles/dates/employers)
- `in_job*` — the job posting you're tailoring toward, as `.docx`, `.pdf`, `.txt`, or
  `.md` (pasting it into a `.txt` file is fine)

To see the expected layout, or to try the tool without your own data, run
`python examples/make_examples.py` and look at the anonymized files in `examples/`.

These folders are git-ignored, so your career data is never committed.

## 4. Run it

**Command Prompt**
```cmd
python generate_resume.py
```

**PowerShell**
```powershell
python generate_resume.py
```

**WSL / bash**
```bash
python3 generate_resume.py
```

The first run will take a minute or so — it's calling Claude to draft and tailor the
content. You'll see progress messages as it works, followed by any warnings it flags
for your review (e.g. a claim it couldn't verify against your source documents —
these are advisory, not errors; read them before sending the resume out).

### Command-line options

| Flag | What it does |
|------|--------------|
| `--job PATH` | Tailor to this posting instead of the newest `resume_input/in_job*` file |
| `--cover-letter` | Also write a cover letter, built only from the validated resume content and held to the same citation and never-claim checks |
| `--archive-job` | After a successful run, move the job posting into `resume_archive/` |
| `--model M`, `--effort E` | Override `CLAUDE_MODEL` / `CLAUDE_EFFORT` for this run |
| `--no-pdf` | Skip the Word-based PDF export |
| `--dry-run` | Generate and validate, print the result, write only a report to your temp dir; nothing is archived or overwritten |

When several `in_*` files match, the most recently modified one is used.

## Output

- `resume_create/out_resume_<first>-<last>_<yyyy-mm-dd>.docx` and `.pdf`: the new
  resume
- `resume_create/out_resume_<first>-<last>_<yyyy-mm-dd>_report.md`: the tailoring
  report. It lists every warning, keyword coverage (posting terms you genuinely have,
  and which of them the resume uses), each bullet with the fact-bank facts it cites,
  the resume's page count (warning over 2 pages), and the raw draft. Read it before
  sending the resume.
- `resume_create/out_cover_letter_<first>-<last>_<yyyy-mm-dd>.docx` and `.pdf`: with
  `--cover-letter`. It is archived the same way as the resume.
- `resume_archive/out_resume_<first>-<last>_<yyyy-mm-dd>-<hh-mm-ss>.docx` (and
  `..._report.md`): whatever was previously in `resume_create/`. The PDF is not
  archived.

## Optional: fact bank and never-claim list

- **`resume_input/fact_bank.yaml`**: one atomic, true fact per entry, tagged with its
  employer. Draft it once with `python build_fact_bank.py`, then edit it by hand. When
  it exists, every bullet must cite fact ids; bullets citing unknown, `unassigned`, or
  another employer's facts are dropped. An employer label that matches no employer in
  your prior resume is flagged as a warning.
- **`do_not_claim.txt`**: one case-insensitive regex per line for claims that must
  never appear (certifications, role identities, tools you don't use). Any match
  aborts the run before anything is written.

## Optional configuration

Create a `.env` file in the repo root to override defaults (none of this is required):

```
CLAUDE_MODEL=sonnet
CLAUDE_EFFORT=medium
CLAUDE_TIMEOUT=600   # seconds per Claude CLI call
```

## Tests

```
pip install -r requirements-dev.txt
python -m pytest -q
```

The tests cover the deterministic parsing and validation code only; they make no
Claude calls.

## Troubleshooting

- **`Could not find the 'claude' CLI on PATH`** — install it (`npm install -g
  @anthropic-ai/claude-code`) and make sure a new terminal picks it up, then run
  `claude /login`.
- **No `.pdf` was created, only a warning** — you're either not on Windows or don't
  have Microsoft Word installed. The `.docx` is fully usable on its own.
- **"Could not parse any employers..." or "Could not find name/email..." errors** —
  the script expects `in_resume*`/`in_profile*` to follow a specific structure (see
  [CLAUDE.md](CLAUDE.md)); check that your files match the expected layout.
