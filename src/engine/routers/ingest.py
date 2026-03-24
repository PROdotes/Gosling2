import os
import shutil
from typing import Optional
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from src.models.view_models import IngestionReportView, SongView
from src.services.catalog_service import CatalogService
from src.services.logger import logger
from src.engine.config import get_db_path, STAGING_DIR, ACCEPTED_EXTENSIONS

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


def _get_service() -> CatalogService:
    """Service factory for the ingestion router."""
    return CatalogService(get_db_path())


def _get_downloads_folder() -> Optional[str]:
    """NT/POSIX compatible downloads folder path."""
    if os.name == "nt":
        return os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")
    elif os.name == "posix":
        home = os.environ.get("HOME", "")
        return os.path.join(home, "Downloads")
    return None


@router.get("/downloads-folder")
async def get_downloads_folder():
    """Retrieve the platform-specific default downloads folder."""
    return JSONResponse({"path": _get_downloads_folder()})


@router.post("/upload", response_model=IngestionReportView)
async def upload_file(file: UploadFile = File(...)) -> IngestionReportView:
    """
    Physical file ingestion entry point.
    1. Validate extension
    2. Save to STAGING_DIR with UUID filename
    3. Orchestrate ingestion via CatalogService
    4. Return IngestionReportView with status and hydrated SongView.
    """
    logger.info(f"[IngestRouter] -> upload_file(filename='{file.filename}')")

    # 1. Extension validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ACCEPTED_EXTENSIONS:
        logger.warning(f"[IngestRouter] Rejected file with extension '{file_ext}'")
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{file_ext}' not allowed. Accepted: {ACCEPTED_EXTENSIONS}",
        )

    # 2. Ensure staging exists
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR, exist_ok=True)

    # 3. Save to staging with UUID filename to prevent collisions
    uuid_filename = f"{uuid4()}_{file.filename}"
    staged_path = os.path.join(STAGING_DIR, uuid_filename)
    try:
        with open(staged_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"[IngestRouter] Failed to save staged file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stage file: {str(e)}")

    # 4. Ingest
    try:
        service = _get_service()
        report = service.ingest_file(staged_path)

        if report["status"] == "ERROR":
            logger.warning(f"[IngestRouter] Ingestion FAILED: {report.get('message')}")
            raise HTTPException(status_code=400, detail=report["message"])

        # 5. Success / Collision
        if "song" in report and report["song"]:
            # Cast Domain Song to SongView for frontend compatibility
            report["song"] = SongView.from_domain(report["song"])

        return IngestionReportView(**report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[IngestRouter] Unexpected ingestion error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal Ingestion Error: {str(e)}"
        )


@router.delete("/songs/{song_id:int}")
async def delete_song(song_id: int):
    """
    Atomic hard-delete of a song by ID.
    Triggers DB cascade and physical cleanup if in staging.
    """
    logger.info(f"[IngestRouter] -> delete_song(id={song_id})")
    service = _get_service()
    success = service.delete_song(song_id)

    if not success:
        logger.warning(f"[IngestRouter] Delete failed: Song ID {song_id} not found.")
        raise HTTPException(status_code=404, detail=f"Song ID {song_id} not found.")

    logger.info(f"[IngestRouter] <- delete_song(id={song_id}) SUCCESS")
    return {"status": "DELETED", "id": song_id}
