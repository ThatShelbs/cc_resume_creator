"""Background jobs: status, cancel, and the live progress stream."""

import asyncio
import json
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..context import Ctx

router = APIRouter()


@router.get("/api/jobs")
def list_jobs(ctx: Ctx):
    return [j.summary() for j in ctx.jobs.active()]


@router.get("/api/jobs/{job_id}")
def get_job(ctx: Ctx, job_id: str, lines: bool = False):
    job = ctx.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job.")
    return {**job.summary(), **({"lines": job.lines} if lines else {})}


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(ctx: Ctx, job_id: str):
    if not ctx.jobs.cancel(job_id):
        raise HTTPException(409, "That job isn't running.")
    return {"ok": True}


@router.get("/api/jobs/{job_id}/events")
async def job_events(ctx: Ctx, job_id: str, request: Request):
    job = ctx.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job.")

    def sse(event: str, data) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    async def stream():
        sent = 0
        last_state = None
        last_beat = time.time()
        while True:
            if await request.is_disconnected():
                return
            batch = job.lines[sent:]
            if batch:
                sent += len(batch)
                yield sse("lines", batch)
            state = (job.status, job.stage, len(job.deny))
            if state != last_state:
                last_state = state
                yield sse("status", job.summary())
            if job.done and sent >= len(job.lines):
                yield sse("end", job.summary())
                return
            if time.time() - last_beat > 15:
                last_beat = time.time()
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
