"""
Resume Taylor: tailors a candidate's real career history to one job posting.

    resume_taylor.pipeline   the resume pipeline (CLI): parsing, the Claude calls,
                             validation guards, docx/pdf output
    resume_taylor.app        the local browser app's FastAPI backend, which runs the
                             pipeline as a subprocess for every generation
    resume_taylor.config     where everything lives (repo, skills, data folders)
    resume_taylor.launcher   starts the app and opens it in the browser
"""

__version__ = "1.0.0"
