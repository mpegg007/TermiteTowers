"""Static image serving endpoints — source images, odo crops, file lookup."""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from water_meter.core.common import IMAGE_DIR, PROC_DIR

from ..utils import find_source_image

router = APIRouter()


@router.get("/images/{subpath:path}")
async def serve_image(subpath: str):
    safe = os.path.normpath(subpath)
    if safe.startswith("..") or os.path.isabs(safe):
        raise HTTPException(status_code=403)
    fp = os.path.join(IMAGE_DIR, safe)
    if not os.path.isfile(fp):
        raise HTTPException(status_code=404)
    return FileResponse(fp, media_type="image/jpeg")


@router.get("/image_file/{image_name}")
async def serve_source_image(image_name: str):
    path = find_source_image(image_name)
    if not path:
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="image/jpeg")


@router.get("/crop/{odo_crop_file:path}")
async def serve_odo_crop(odo_crop_file: str):
    path = os.path.join(PROC_DIR, odo_crop_file)
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="image/jpeg")
