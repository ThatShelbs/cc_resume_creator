# Resume Taylor backend

Python package `resume_taylor` (src layout). Two halves:

- `pipeline/`: the resume pipeline. `python -m resume_taylor.pipeline --help`
  (or the `generate_resume.py` shim at the repo root). Deterministic parsing,
  the Claude calls, the validation guards, docx/pdf output.
- `app/`: the FastAPI backend of the browser app (`routers/`, `services/`,
  `storage/`). It runs the pipeline as a subprocess for every generation.

Shared modules: `layout.py` (folder locations, stdlib only), `config.py`
(environment and default files), `claude_cli.py` (running the `claude` CLI),
`launcher.py` (starts the app), `sample_data/` (the fictional demo applicant),
`resources/` (the starter never-claim list).

## Develop

```
pip install -e "backend[dev]"
python -m pytest -q         # from backend/ (or the repo root)
ruff check backend
```
