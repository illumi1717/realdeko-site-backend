import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "media"))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

media_router = APIRouter(prefix="/media", tags=["media"])


@media_router.post("/upload")
async def upload_media(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")

    extension = Path(file.filename).suffix
    safe_extension = extension if len(extension) <= 5 else ""
    target_name = f"{uuid.uuid4().hex}{safe_extension}"
    target_path = MEDIA_ROOT / target_name

    try:
        with target_path.open("wb") as buffer:
            buffer.write(await file.read())
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save file")

    # Return a relative URL that is served by StaticFiles in main.py
    return JSONResponse({"url": f"/media/{target_name}"})

