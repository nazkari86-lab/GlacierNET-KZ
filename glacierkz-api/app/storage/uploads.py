import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import MAX_FILE_SIZE_BYTES, UPLOAD_DIR

ALLOWED_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
CHUNK_SIZE = 64 * 1024


async def save_upload(file: UploadFile) -> Path:
    ext = Path(file.filename or "image.tif").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format: {ext}. Allowed: {ALLOWED_EXTENSIONS}")

    file_id = uuid.uuid4().hex[:12]
    save_path = UPLOAD_DIR / f"{file_id}{ext}"

    total = 0
    with open(save_path, "wb") as buf:
        while chunk := await file.read(CHUNK_SIZE):
            total += len(chunk)
            if total > MAX_FILE_SIZE_BYTES:
                save_path.unlink(missing_ok=True)
                raise HTTPException(413, f"File too large. Max: {MAX_FILE_SIZE_BYTES // 1024**2} MB")
            buf.write(chunk)

    return save_path
