"""Sample data: load a fictional applicant to try the app, or clear it again."""

from fastapi import APIRouter, HTTPException

from ..context import Ctx
from ..services import demo

router = APIRouter()


@router.post("/api/demo/load")
def load_demo(ctx: Ctx):
    if ctx.jobs.active():
        raise HTTPException(409, "Wait for the running task to finish first.")
    try:
        demo.load_sample(ctx.paths)
    except demo.SampleError as exc:
        raise HTTPException(409, str(exc)) from None
    ctx.invalidate_sources()
    return {"ok": True}


@router.post("/api/demo/clear")
def clear_demo(ctx: Ctx):
    if ctx.jobs.active():
        raise HTTPException(409, "Wait for the running task to finish first.")
    try:
        result = demo.clear_sample(ctx.paths)
    except demo.SampleError as exc:
        raise HTTPException(409, str(exc)) from None
    ctx.invalidate_sources()
    return result
