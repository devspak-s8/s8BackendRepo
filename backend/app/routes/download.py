# app/routes/downloads.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import tempfile

router = APIRouter(prefix="/downloads", tags=["Downloads"])

ZIP_DIR = tempfile.gettempdir()  # Same folder where zips are generated

@router.get("/{zip_name}")
async def download_zip(zip_name: str):
    """
    Download a generated zip file.
    """
    zip_path = os.path.join(ZIP_DIR, zip_name)

    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=zip_path,
        filename=zip_name,
        media_type='application/zip'
    )
