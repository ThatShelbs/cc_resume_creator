"""App settings and the optional saved API key."""

from fastapi import APIRouter, HTTPException

from ..context import Ctx
from ..schemas import ApiKeyBody
from ..storage import credentials
from ..storage.settings import Settings, save_settings

router = APIRouter()


@router.get("/api/settings")
def get_settings(ctx: Ctx):
    return ctx.settings()


@router.put("/api/settings")
def put_settings(ctx: Ctx, body: Settings):
    save_settings(ctx.paths.settings_path, body)
    return body


@router.get("/api/settings/api-key")
def get_api_key(ctx: Ctx):
    return credentials.status(ctx.paths.secrets_path)


@router.put("/api/settings/api-key")
def put_api_key(ctx: Ctx, body: ApiKeyBody):
    try:
        credentials.save_key(ctx.paths.secrets_path, body.key)
    except credentials.BadKey as exc:
        raise HTTPException(400, str(exc)) from None
    ctx.claude.forget_login()
    return credentials.status(ctx.paths.secrets_path)


@router.delete("/api/settings/api-key")
def delete_api_key(ctx: Ctx):
    credentials.clear_key(ctx.paths.secrets_path)
    return credentials.status(ctx.paths.secrets_path)
