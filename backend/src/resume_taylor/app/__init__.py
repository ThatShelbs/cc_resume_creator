"""
Resume Taylor's local browser app: a FastAPI backend over the resume pipeline.

The app never tailors anything itself. It keeps the pipeline's canonical inputs
(resume_input/in_profile*.docx, in_resume*.docx, fact_bank.yaml, do_not_claim.txt)
in the exact layout the pipeline parses, stores one folder per job application
under projects/, and runs the pipeline as a subprocess for every generation or
re-render. The tailoring rules still live only in .claude/skills/.

    main.py       create_app(): wires everything together
    context.py    shared per-app state and helpers (injected into routes)
    routers/      the HTTP API, one module per area
    services/     background jobs, live lint checks, sample data, system status
    storage/      files on disk: paths, projects, profile, facts, settings, ...
"""
