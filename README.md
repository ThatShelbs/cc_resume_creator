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
- `in_job*.docx` — the job posting you're tailoring toward

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

## Output

- `resume_create/out_resume_<first>-<last>_<yyyy-mm-dd>.docx` and `.pdf` — the new
  resume
- `resume_archive/out_resume_<first>-<last>_<yyyy-mm-dd>-<hh-mm-ss>.docx` — whatever
  was previously in `resume_create/`, kept as `.docx` only

## Optional configuration

Create a `.env` file in the repo root to override defaults (none of this is required):

```
CLAUDE_MODEL=sonnet
CLAUDE_EFFORT=medium
```

## Troubleshooting

- **`Could not find the 'claude' CLI on PATH`** — install it (`npm install -g
  @anthropic-ai/claude-code`) and make sure a new terminal picks it up, then run
  `claude /login`.
- **No `.pdf` was created, only a warning** — you're either not on Windows or don't
  have Microsoft Word installed. The `.docx` is fully usable on its own.
- **"Could not parse any employers..." or "Could not find name/email..." errors** —
  the script expects `in_resume*`/`in_profile*` to follow a specific structure (see
  [CLAUDE.md](CLAUDE.md)); check that your files match the expected layout.
