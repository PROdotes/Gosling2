import os
import shutil
from typing import Optional
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from src.models.view_models import (
    SongView,
    FolderScanRequest,
    BatchIngestReport,
)
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


@router.get("/formats")
async def get_accepted_formats():
    """Retrieve the list of supported file extensions for ingestion."""
    return JSONResponse({"extensions": ACCEPTED_EXTENSIONS})


@router.post("/upload", response_model=BatchIngestReport)
async def upload_files(files: list[UploadFile] = File(...)) -> BatchIngestReport:
    """
    Physical file ingestion entry point (supports batch uploads).
    Browser automatically flattens folders into individual files.

    1. Validate extensions
    2. Save all files to STAGING_DIR with UUID filenames
    3. Orchestrate batch ingestion via CatalogService
    4. Return BatchIngestReport with aggregate stats and per-file results.
    """
    logger.info(f"[IngestRouter] -> upload_files(count={len(files)})")

    # 1. Ensure staging exists
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR, exist_ok=True)

    # 2. Stage all valid files
    staged_paths = []
    for file in files:
        # Validate filename
        if not file.filename:
            logger.warning("[IngestRouter] Skipping file with no filename")
            continue

        # Validate extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ACCEPTED_EXTENSIONS:
            logger.warning(
                f"[IngestRouter] Skipping file with invalid extension '{file_ext}': {file.filename}"
            )
            continue

        # Save to staging with UUID filename to prevent collisions
        uuid_filename = f"{uuid4()}_{file.filename}"
        staged_path = os.path.join(STAGING_DIR, uuid_filename)

        try:
            with open(staged_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            staged_paths.append(staged_path)
            logger.debug(f"[IngestRouter] Staged: {file.filename} -> {staged_path}")
        except Exception as e:
            logger.error(f"[IngestRouter] Failed to stage {file.filename}: {e}")
            # Continue with other files instead of failing the entire batch

    if not staged_paths:
        raise HTTPException(
            status_code=400,
            detail=f"No valid audio files found. Accepted extensions: {ACCEPTED_EXTENSIONS}",
        )

    # 3. Batch ingest
    try:
        service = _get_service()
        batch_report = service.ingest_batch(staged_paths)

        # 4. Convert Domain Songs to SongViews for frontend compatibility
        for result in batch_report["results"]:
            if "song" in result and result["song"]:
                result["song"] = SongView.from_domain(result["song"])

        return BatchIngestReport(**batch_report)

    except Exception as e:
        logger.error(f"[IngestRouter] Batch ingestion error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal Ingestion Error: {str(e)}"
        )


@router.post("/scan-folder", response_model=BatchIngestReport)
async def scan_folder(request: FolderScanRequest) -> BatchIngestReport:
    """
    Server-side folder scanning and ingestion.
    Scans a local filesystem path for audio files and ingests them.

    Use this for desktop app or when files are already on the server.
    For browser uploads, use /upload instead.

    Example:
        POST /api/v1/ingest/scan-folder
        {
            "folder_path": "Z:\\Songs\\New Album",
            "recursive": true
        }
    """
    logger.info(
        f"[IngestRouter] -> scan_folder(path='{request.folder_path}', recursive={request.recursive})"
    )

    # 1. Scan for audio files
    service = _get_service()
    audio_files = service.scan_folder(request.folder_path, request.recursive)

    if not audio_files:
        raise HTTPException(
            status_code=404,
            detail=f"No audio files found in {request.folder_path}. Accepted extensions: {ACCEPTED_EXTENSIONS}",
        )

    # 2. Ensure staging exists
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR, exist_ok=True)

    # 3. Copy files to staging
    staged_paths = []
    for file_path in audio_files:
        try:
            uuid_filename = f"{uuid4()}_{Path(file_path).name}"
            staged_path = os.path.join(STAGING_DIR, uuid_filename)
            shutil.copy2(file_path, staged_path)
            staged_paths.append(staged_path)
            logger.debug(f"[IngestRouter] Staged: {file_path} -> {staged_path}")
        except Exception as e:
            logger.error(f"[IngestRouter] Failed to stage {file_path}: {e}")
            # Continue with other files

    if not staged_paths:
        raise HTTPException(
            status_code=500, detail="Failed to stage any files for ingestion"
        )

    # 4. Batch ingest
    try:
        batch_report = service.ingest_batch(staged_paths)

        # 5. Convert Domain Songs to SongViews
        for result in batch_report["results"]:
            if "song" in result and result["song"]:
                result["song"] = SongView.from_domain(result["song"])

        logger.info(
            f"[IngestRouter] <- scan_folder() "
            f"found={len(audio_files)} ingested={batch_report['ingested']}"
        )
        return BatchIngestReport(**batch_report)

    except Exception as e:
        logger.error(f"[IngestRouter] Folder scan ingestion error: {e}")
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
