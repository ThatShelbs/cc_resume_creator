"""Request bodies for the HTTP API."""

from pydantic import BaseModel

from .storage import facts as facts_mod
from .storage import resume_ingest


class NewProject(BaseModel):
    job_text: str
    company: str = ""
    role: str = ""
    name: str = ""
    url: str = ""
    template: str | None = None
    cover_letter: bool | None = None
    generate: bool = False


class ProjectPatch(BaseModel):
    name: str | None = None
    company: str | None = None
    role: str | None = None
    url: str | None = None
    status: str | None = None
    notes: str | None = None
    applied_on: str | None = None
    template: str | None = None
    cover_letter: bool | None = None


class TextBody(BaseModel):
    text: str


class RenderBody(BaseModel):
    template: str | None = None


class ResumeConfirm(BaseModel):
    structure: resume_ingest.ResumeStructure
    upload_id: str | None = None


class FactsBody(BaseModel):
    facts: list[facts_mod.Fact]


class DraftFactsBody(BaseModel):
    force: bool = False


class PhraseBody(BaseModel):
    text: str
    phrase: str


class ImportBody(BaseModel):
    files: list[str]


class ApiKeyBody(BaseModel):
    key: str


class OpenFolderBody(BaseModel):
    target: str = "data"
