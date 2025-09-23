# app/utils/b2_utils.py
from b2sdk.v2 import InMemoryAccountInfo, B2Api
from pathlib import Path
from s8.core.config import settings

info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account(
    "production",
    settings.B2_KEY_ID,
    settings.B2_APPLICATION_KEY
)
bucket = b2_api.get_bucket_by_name(settings.B2_BUCKET_NAME)


def get_signed_url(file_name: str, ttl_seconds: int = 3600) -> str:
    """
    Generate a signed URL for a private Backblaze B2 file valid for ttl_seconds
    """
    # signed download URL
    return bucket.get_download_url(file_name, valid_duration=ttl_seconds)


def upload_image_to_b2(file_path: Path) -> str:
    """
    Uploads a local file to Backblaze B2 and returns the public/private URL.
    """
    file_name = file_path.name

    # correct method for uploading local files
    bucket.upload_local_file(
        local_file=str(file_path),
        file_name=file_name,
        content_type="image/jpeg"
    )

    if settings.B2_BUCKET_PUBLIC:
        # Public URL
        return f"https://f000.backblazeb2.com/file/{settings.B2_BUCKET_NAME}/{file_name}"
    else:
        # Private bucket → return file name (signed URL can be generated later)
        return file_name
