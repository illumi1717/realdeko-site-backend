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


def _resolve_path_from_url(url: str) -> Path:
    # Accept both absolute (/media/xxx) and relative (xxx) inputs.
    cleaned = url.replace("/media/", "").replace("\\", "/").strip("/")
    target_path = MEDIA_ROOT / cleaned
    # Prevent escaping the media directory.
    if not target_path.resolve().is_relative_to(MEDIA_ROOT.resolve()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid media path")
    return target_path


@media_router.delete("")
async def delete_media(url: str):
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="url is required")
    target_path = _resolve_path_from_url(url)
    if target_path.exists():
        try:
            target_path.unlink()
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete file")
    return {"message": "deleted"}

