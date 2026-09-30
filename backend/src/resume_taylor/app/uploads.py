"""Reading and validating file uploads."""

import re
from pathlib import Path

from fastapi import HTTPException, UploadFile

MAX_UPLOAD = 20 * 1024 * 1024


async def read_upload(file: UploadFile, allowed: tuple) -> tuple[str, bytes]:
    name = Path(file.filename or "upload").name
    ext = Path(name).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Upload a {' or '.join(allowed)} file.")
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "That file is larger than 20 MB.")
    if not data:
        raise HTTPException(400, "That file is empty.")
    safe = re.sub(r"[^\w.\- ]+", "_", Path(name).stem).strip() or "upload"
    return f"{safe}{ext}", data
