"""App preferences (model, effort, timeout, default template), kept in
app_settings.json. These become pipeline flags per run; .env still
works for the CLI."""

import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from resume_taylor.config import EFFORT, MODEL
from resume_taylor.pipeline.render.templates import DEFAULT_TEMPLATE, TEMPLATES

MODEL_CHOICES = ["sonnet", "opus", "haiku"]
EFFORT_CHOICES = ["low", "medium", "high"]


class Settings(BaseModel):
    model: str = Field(default_factory=lambda: MODEL)
    effort: str = Field(default_factory=lambda: EFFORT)
    timeout_seconds: int = Field(default=900, ge=60, le=3600)
    default_template: str = DEFAULT_TEMPLATE
    cover_letter_default: bool = False

    @field_validator("model")
    @classmethod
    def _model(cls, v: str) -> str:
        v = v.strip()
        if not v or any(c.isspace() for c in v):
            raise ValueError("model must be a single word such as 'sonnet'")
        return v

    @field_validator("effort")
    @classmethod
    def _effort(cls, v: str) -> str:
        if v not in EFFORT_CHOICES:
            raise ValueError(f"effort must be one of {', '.join(EFFORT_CHOICES)}")
        return v

    @field_validator("default_template")
    @classmethod
    def _template(cls, v: str) -> str:
        if v not in TEMPLATES:
            raise ValueError(f"unknown template '{v}'")
        return v


def load_settings(path: Path) -> Settings:
    try:
        return Settings(**json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return Settings()


def save_settings(path: Path, settings: Settings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
