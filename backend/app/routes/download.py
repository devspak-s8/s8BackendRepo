# app/routes/downloads.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import tempfile

router = APIRouter(prefix="/downloads", tags=["Downloads"])

# Directory where ZIP files are temporarily stored
ZIP_DIR = tempfile.gettempdir()  # same folder used in generate_app.py

@router.get("/{zip_name}")
async def download_zip(zip_name: str):
    """
    Download a previously generated ZIP file by its name.
    """
    zip_path = os.path.join(ZIP_DIR, zip_name)

    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=zip_path,
        filename=zip_name,    # sets the download filename
        media_type="application/zip"
    )
